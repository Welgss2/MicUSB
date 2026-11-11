import AVFoundation
import Network

struct MicrophoneOption: Identifiable, Hashable {
    let id: String
    let name: String
}

/// Captura o microfone (PCM 16-bit, 48 kHz, mono) e envia por TCP na porta 5000.
/// O PC acessa essa porta pelo cabo USB (usbmuxd).
final class MicStreamer: ObservableObject {
    @Published var status = "Parado"
    @Published var clients = 0
    @Published var running = false
    @Published var microphoneOptions: [MicrophoneOption] = []
    @Published var selectedMicrophoneID = UserDefaults.standard.string(forKey: "MicUSB.selectedMic") ?? ""

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
            try configureBuiltInMicrophone(session)
            try startListener()
            try installCaptureTap()
            running = true
            status = "Transmitindo na porta 5000.\nConecte o cabo e abra o programa no PC."
        } catch {
            status = "Erro: \(error.localizedDescription)"
        }
    }

    private func configureBuiltInMicrophone(_ session: AVAudioSession) throws {
        guard let mic = session.availableInputs?.first(where: { $0.portType == .builtInMic }) else {
            microphoneOptions = [MicrophoneOption(id: "auto", name: "Automático (iOS)")]
            selectedMicrophoneID = "auto"
            return
        }

        try session.setPreferredInput(mic)
        let sources = mic.dataSources ?? []
        microphoneOptions = sources.enumerated().map { index, source in
            let raw = source.dataSourceName
            let key = raw.lowercased()
            let friendly: String
            if key.contains("bottom") || key.contains("lower") || key.contains("inferior") {
                friendly = "Inferior — base do iPhone"
            } else if key.contains("front") || key.contains("frontal") {
                friendly = "Frontal — lado da tela"
            } else if key.contains("back") || key.contains("rear") || key.contains("traseiro") {
                friendly = "Traseiro — lado das câmeras"
            } else {
                friendly = raw
            }
            return MicrophoneOption(id: source.dataSourceID.stringValue,
                                    name: "\(index + 1). \(friendly)")
        }

        guard !sources.isEmpty else {
            selectedMicrophoneID = "auto"
            return
        }
        let chosen = sources.first(where: { $0.dataSourceID.stringValue == selectedMicrophoneID }) ?? sources[0]
        if chosen.supportedPolarPatterns?.contains(.cardioid) == true {
            try chosen.setPreferredPolarPattern(.cardioid)
        }
        try mic.setPreferredDataSource(chosen)
        selectedMicrophoneID = chosen.dataSourceID.stringValue
        UserDefaults.standard.set(selectedMicrophoneID, forKey: "MicUSB.selectedMic")
    }

    private func installCaptureTap() throws {
        let input = engine.inputNode
        let inFormat = input.outputFormat(forBus: 0)
        let outFormat = AVAudioFormat(commonFormat: .pcmFormatInt16, sampleRate: 48000,
                                      channels: 1, interleaved: true)!
        guard let converter = AVAudioConverter(from: inFormat, to: outFormat) else {
            throw NSError(domain: "MicUSB", code: 1,
                          userInfo: [NSLocalizedDescriptionKey: "Erro ao configurar o conversor de áudio"])
        }

        // One DeepFilterNet frame (512 samples at 48 kHz) reduces capture buffering to ~10.7 ms.
        input.installTap(onBus: 0, bufferSize: 512, format: inFormat) { [weak self] buf, _ in
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
                for connection in self.connections {
                    connection.send(content: data, completion: .contentProcessed { _ in })
                }
            }
        }
        try engine.start()
    }

    func selectMicrophone(_ id: String) {
        selectedMicrophoneID = id
        UserDefaults.standard.set(id, forKey: "MicUSB.selectedMic")
        guard running else { return }

        do {
            engine.stop()
            engine.inputNode.removeTap(onBus: 0)
            let session = AVAudioSession.sharedInstance()
            try session.setActive(false)
            try session.setActive(true)
            try configureBuiltInMicrophone(session)
            try installCaptureTap()
            status = "Microfone alterado. Transmitindo na porta 5000."
        } catch {
            status = "Erro ao trocar o microfone: \(error.localizedDescription)"
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
