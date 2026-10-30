import BetaKit
import SwiftUI

struct BetaView: View {
    @Environment(AppModel.self) private var model
    @State private var sent: Set<FeedbackKind> = []

    var body: some View {
        let session = model.session
        if let beta = session.beta {
            List {
                Section {
                    VStack(alignment: .leading, spacing: 8) {
                        HStack(alignment: .firstTextBaseline) {
                            Text(beta.grade ?? "V?").font(.largeTitle.bold())
                            if let font = beta.gradeFont { Text("Font \(font)").foregroundStyle(.secondary) }
                            Spacer()
                            if let confidence = beta.confidence {
                                Text("\(Int(confidence * 100))% sure").font(.caption).foregroundStyle(.secondary)
                            }
                        }
                        Text(beta.summary)
                    }
                }

                Section("Route video") {
                    switch session.videoState {
                    case .none:
                        Button {
                            Task { await session.makeVideo() }
                        } label: {
                            Label("Watch it climbed", systemImage: "play.rectangle")
                        }
                    case .working:
                        HStack(spacing: 12) {
                            ProgressView()
                            Text("Directing and rendering your video…")
                        }
                    case .ready(let video):
                        RouteVideoView(video: video, moves: beta.moves)
                    case .failed(let message):
                        Text(message).foregroundStyle(.secondary)
                        Button("Try again") { Task { await session.makeVideo() } }
                    }
                }

                Section("Moves") {
                    ForEach(beta.moves) { move in
                        MoveRow(move: move)
                    }
                }

                Section("How did it go?") {
                    HStack {
                        feedbackButton("Sent it", kind: .sent, symbol: "checkmark.seal")
                        feedbackButton("Useful", kind: .useful, symbol: "hand.thumbsup")
                        feedbackButton("Not for me", kind: .notUseful, symbol: "hand.thumbsdown")
                    }
                    .buttonStyle(.bordered)
                }

                Section {
                    Text("Beta is a suggestion. Climb within your ability and check your landing.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
        }
    }

    private func feedbackButton(_ title: String, kind: FeedbackKind, symbol: String) -> some View {
        Button {
            sent.insert(kind)
            Task { await model.session.sendFeedback(kind) }
        } label: {
            Label(title, systemImage: sent.contains(kind) ? "\(symbol).fill" : symbol)
                .labelStyle(.titleAndIcon)
                .font(.footnote)
        }
        .disabled(sent.contains(kind))
    }
}

struct MoveRow: View {
    let move: Move

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Circle()
                .fill(Color.limb(move.limb))
                .frame(width: 12, height: 12)
                .padding(.top, 6)
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text("\(move.index + 1). \(move.limb.label)").font(.headline)
                    Text(move.techniqueLabel)
                        .font(.caption)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(.thinMaterial, in: .capsule)
                    if move.isCrux {
                        Text("CRUX").font(.caption.bold()).foregroundStyle(Color.accentOrange)
                    }
                }
                Text(move.cue).foregroundStyle(.secondary)
            }
        }
        .accessibilityElement(children: .combine)
    }
}
