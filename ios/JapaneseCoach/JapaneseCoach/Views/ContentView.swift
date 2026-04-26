import SwiftUI

struct ContentView: View {
    @StateObject private var viewModel = TutorViewModel()
    @State private var isPressingHoldButton = false

    var body: some View {
        GeometryReader { proxy in
            ZStack {
                LinearGradient(
                    colors: [
                        Color(red: 0.98, green: 0.96, blue: 0.92),
                        Color(red: 0.91, green: 0.84, blue: 0.75),
                        Color(red: 0.76, green: 0.37, blue: 0.28),
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 18) {
                        headerCard
                        modeCard
                        holdButton
                        transcriptCard(title: "You Said", text: viewModel.transcriptText.isEmpty ? "Nothing captured yet." : viewModel.transcriptText)
                        transcriptCard(title: "Yuki", text: viewModel.assistantText.isEmpty ? "No reply yet." : viewModel.assistantText)

                        if !viewModel.englishHintText.isEmpty {
                            transcriptCard(title: "English Help", text: viewModel.englishHintText)
                        }

                        if !viewModel.pronunciationText.isEmpty {
                            transcriptCard(title: "Shadow Feedback", text: viewModel.pronunciationText)
                        }

                        helperCard
                        quickActions
                    }
                    .frame(maxWidth: .infinity)
                    .frame(minHeight: proxy.size.height, alignment: .top)
                    .padding(20)
                }
                .scrollIndicators(.hidden)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        }
    }

    private var headerCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Japanese Coach")
                .font(.system(size: 30, weight: .black, design: .rounded))
                .foregroundStyle(Color(red: 0.25, green: 0.08, blue: 0.06))

            Text("Local-first speaking practice powered by your PC.")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            TextField("192.168.1.10:8765", text: $viewModel.settings.serverHost)
                .textInputAutocapitalization(.never)
                .disableAutocorrection(true)
                .padding(14)
                .background(.white.opacity(0.85), in: RoundedRectangle(cornerRadius: 16, style: .continuous))

            HStack(spacing: 12) {
                Button(viewModel.connectionState == .connected ? "Disconnect" : "Connect") {
                    if viewModel.connectionState == .connected {
                        viewModel.disconnect()
                    } else {
                        viewModel.connect()
                    }
                }
                .buttonStyle(FilledPillButtonStyle(fill: .black))

                Toggle("Auto speak", isOn: $viewModel.settings.autoSpeakJapanese)
                    .toggleStyle(.switch)
            }

            Text(viewModel.statusText)
                .font(.footnote.weight(.semibold))
                .foregroundStyle(Color(red: 0.41, green: 0.12, blue: 0.08))

            if !viewModel.modelText.isEmpty || !viewModel.vocabText.isEmpty {
                HStack {
                    if !viewModel.modelText.isEmpty {
                        Label(viewModel.modelText, systemImage: "cpu")
                    }
                    Spacer()
                    if !viewModel.vocabText.isEmpty {
                        Label(viewModel.vocabText, systemImage: "book.closed")
                    }
                }
                .font(.caption)
                .foregroundStyle(.secondary)
            }
        }
        .padding(20)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 28, style: .continuous))
    }

    private var modeCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Mode")
                .font(.headline)

            Picker("Mode", selection: $viewModel.selectedMode) {
                ForEach(TutorMode.allCases) { mode in
                    Text(mode.title).tag(mode)
                }
            }
            .pickerStyle(.segmented)

            Text(viewModel.selectedMode.subtitle)
                .font(.footnote)
                .foregroundStyle(.secondary)
        }
        .padding(18)
        .background(Color.white.opacity(0.78), in: RoundedRectangle(cornerRadius: 24, style: .continuous))
    }

    private var holdButton: some View {
        VStack(spacing: 14) {
            Text(viewModel.isRecording ? "Release to send" : "Hold to talk")
                .font(.headline)
                .foregroundStyle(Color.white)

            Circle()
                .fill(
                    LinearGradient(
                        colors: viewModel.isRecording
                            ? [Color.red, Color.orange]
                            : [Color(red: 0.31, green: 0.07, blue: 0.06), Color(red: 0.73, green: 0.21, blue: 0.16)],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .frame(width: 220, height: 220)
                .overlay {
                    VStack(spacing: 8) {
                        Image(systemName: viewModel.isRecording ? "waveform.circle.fill" : "mic.fill")
                            .font(.system(size: 38, weight: .bold))
                        Text(viewModel.isRecording ? "Release" : "Hold")
                            .font(.system(size: 24, weight: .black, design: .rounded))
                    }
                    .foregroundStyle(.white)
                }
                .shadow(color: .black.opacity(0.22), radius: 20, y: 12)
                .gesture(
                    DragGesture(minimumDistance: 0)
                        .onChanged { _ in
                            if !isPressingHoldButton {
                                isPressingHoldButton = true
                                viewModel.beginTalking()
                            }
                        }
                        .onEnded { _ in
                            isPressingHoldButton = false
                            viewModel.endTalking()
                        }
                )
        }
        .padding(.vertical, 12)
    }

    private func transcriptCard(title: String, text: String) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title)
                .font(.headline)
                .foregroundStyle(Color(red: 0.28, green: 0.09, blue: 0.07))

            Text(text)
                .font(.body)
                .foregroundStyle(.primary)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(18)
        .background(Color.white.opacity(0.82), in: RoundedRectangle(cornerRadius: 24, style: .continuous))
    }

    private var helperCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Coach Note")
                .font(.headline)
                .foregroundStyle(Color(red: 0.28, green: 0.09, blue: 0.07))

            Text(viewModel.helperText)
                .font(.body)
        }
        .padding(18)
        .background(Color(red: 0.23, green: 0.10, blue: 0.08).opacity(0.88), in: RoundedRectangle(cornerRadius: 24, style: .continuous))
        .foregroundStyle(.white)
    }

    private var quickActions: some View {
        HStack(spacing: 12) {
            Button("Explain Last") {
                viewModel.explainLast()
            }
            .buttonStyle(FilledPillButtonStyle(fill: Color.white.opacity(0.84), foreground: .black))

            Button("Repeat") {
                viewModel.repeatLast()
            }
            .buttonStyle(FilledPillButtonStyle(fill: Color.white.opacity(0.84), foreground: .black))

            Button("Stop Voice") {
                viewModel.stopSpeaking()
            }
            .buttonStyle(FilledPillButtonStyle(fill: Color.black.opacity(0.84)))
        }
        .font(.subheadline.weight(.bold))
    }
}

private struct FilledPillButtonStyle: ButtonStyle {
    var fill: Color
    var foreground: Color = .white

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .frame(maxWidth: .infinity)
            .background(fill.opacity(configuration.isPressed ? 0.72 : 1.0), in: Capsule())
            .foregroundStyle(foreground)
            .scaleEffect(configuration.isPressed ? 0.98 : 1.0)
    }
}
