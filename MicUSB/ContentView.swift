import SwiftUI

struct ContentView: View {
    @StateObject private var streamer = MicStreamer()

    var body: some View {
        VStack(spacing: 24) {
            Text("MicUSB").font(.largeTitle).bold()
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
