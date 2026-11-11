import AVFoundation
import Network

/// Captura o microfone (PCM 16-bit, 48 kHz, mono) e envia por TCP na porta 5000.
/// O PC acessa essa porta pelo cabo USB (usbmuxd).
final class MicStreamer: ObservableObject {
    @Published var status = "Parado"
    @Published var clients = 0
    @Published var running = false

    static let port: NWEndpoint.Port = 5000
    private let engine = AVAudioEngine()
    private var listener: NWListener?
    private var connections: [NWConnection] = []
    private let queue = DispatchQueue(label: "micusb.net")

    func start() {
        AVAudioSession.sharedInstance().requestRecordPermission { granted in
            DispatchQueue.main.async {
                if granted { self.begin() } else { self.status = "Sem permissão do microfone" }
            }
        }
    }

    private func begin() {
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playAndRecord, mode: .measurement, options: [])
            try session.setPreferredSampleRate(48000)
            try session.setActive(true)

            let input = engine.inputNode
            let inFormat = input.outputFormat(forBus: 0)
            let outFormat = AVAudioFormat(commonFormat: .pcmFormatInt16, sampleRate: 48000,
                                          channels: 1, interleaved: true)!
            guard let converter = AVAudioConverter(from: inFormat, to: outFormat) else {
                status = "Erro: conversor de áudio"; return
            }

            input.installTap(onBus: 0, bufferSize: 1024, format: inFormat) { [weak self] buf, _ in
                guard let self = self else { return }
                let ratio = outFormat.sampleRate / inFormat.sampleRate
                let cap = AVAudioFrameCount(Double(buf.frameLength) * ratio) + 32
                guard let out = AVAudioPCMBuffer(pcmFormat: outFormat, frameCapacity: cap) else { return }
                var supplied = false
                var err: NSError?
                converter.convert(to: out, error: &err) { _, status in
                    if supplied { status.pointee = .noDataNow; return nil }
                    supplied = true
                    status.pointee = .haveData
                    return buf
                }
                guard err == nil, out.frameLength > 0, let ch = out.int16ChannelData else { return }
                let data = Data(bytes: ch[0], count: Int(out.frameLength) * 2)
                self.queue.async {
                    for c in self.connections {
                        c.send(content: data, completion: .contentProcessed { _ in })
                    }
                }
            }

            try startListener()
            try engine.start()
            running = true
            status = "Transmitindo na porta 5000.\nConecte o cabo e abra o programa no PC."
        } catch {
            status = "Erro: \(error.localizedDescription)"
        }
    }

    private func startListener() throws {
        let tcp = NWProtocolTCP.Options()
        tcp.noDelay = true
        let params = NWParameters(tls: nil, tcp: tcp)
        params.allowLocalEndpointReuse = true
        let l = try NWListener(using: params, on: Self.port)
        l.newConnectionHandler = { [weak self] conn in
            guard let self = self else { return }
            conn.stateUpdateHandler = { state in
                switch state {
                case .failed, .cancelled:
                    self.queue.async {
                        self.connections.removeAll { $0 === conn }
                        self.publishCount()
                    }
                default: break
                }
            }
            self.queue.async {
                self.connections.append(conn)
                self.publishCount()
            }
            conn.start(queue: self.queue)
        }
        l.start(queue: queue)
        listener = l
    }

    private func publishCount() {
        let n = connections.count
        DispatchQueue.main.async { self.clients = n }
    }

    func stop() {
        engine.inputNode.removeTap(onBus: 0)
        engine.stop()
        listener?.cancel(); listener = nil
        queue.async { self.connections.forEach { $0.cancel() }; self.connections.removeAll(); self.publishCount() }
        try? AVAudioSession.sharedInstance().setActive(false)
        running = false
        status = "Parado"
    }
}
