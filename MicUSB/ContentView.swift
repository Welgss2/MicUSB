import SwiftUI

struct ContentView: View {
    @StateObject private var streamer = MicStreamer()

    var body: some View {
        VStack(spacing: 24) {
            Text("MicUSB").font(.largeTitle).bold()
            if !streamer.microphoneOptions.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Microfone do iPhone").font(.headline)
                    Picker("Microfone", selection: $streamer.selectedMicrophoneID) {
                        ForEach(streamer.microphoneOptions) { option in
                            Text(option.name).tag(option.id)
                        }
                    }
                    .pickerStyle(.menu)
                    .onChange(of: streamer.selectedMicrophoneID) { newID in
                        streamer.selectMicrophone(newID)
                    }
                    Text("Escolha a direção do microfone. Selecione a que aponta para sua voz.")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding()
                .background(Color(.secondarySystemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 12))
            }
            Text(streamer.status).multilineTextAlignment(.center)
            Text("PCs conectados: \(streamer.clients)").foregroundColor(.secondary)
            Button(streamer.running ? "Parar" : "Iniciar") {
                streamer.running ? streamer.stop() : streamer.start()
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
        }
        .padding()
        .onAppear { if !streamer.running { streamer.start() } }
    }
}
