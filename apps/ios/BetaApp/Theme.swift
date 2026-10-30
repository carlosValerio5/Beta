import BetaKit
import SwiftUI

extension Color {
    init(hex: String) {
        let c = Palette.rgb(hex)
        self.init(red: c.red, green: c.green, blue: c.blue)
    }

    static let ink = Color(hex: Palette.inkHex)
    static let chalk = Color(hex: Palette.chalkHex)
    static let accentOrange = Color(hex: Palette.accentHex)

    static func limb(_ limb: Limb) -> Color {
        Color(hex: Palette.limbHex[limb] ?? Palette.chalkHex)
    }

    static func hold(_ name: String) -> Color {
        Color(hex: Palette.holdHex[name] ?? "#888888")
    }
}

/// Aspect-fit size of `content` inside `container`.
func aspectFit(_ content: CGSize, in container: CGSize) -> CGSize {
    guard content.width > 0, content.height > 0 else { return .zero }
    let scale = min(container.width / content.width, container.height / content.height)
    return CGSize(width: content.width * scale, height: content.height * scale)
}

struct WorkingView: View {
    let title: String
    var subtitle: String?

    var body: some View {
        VStack(spacing: 16) {
            ProgressView().controlSize(.large)
            Text(title).font(.title3.bold())
            if let subtitle { Text(subtitle).foregroundStyle(.secondary) }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct FailureView: View {
    let message: String
    let retry: () -> Void

    var body: some View {
        ContentUnavailableView {
            Label("Something went wrong", systemImage: "exclamationmark.triangle")
        } description: {
            Text(message)
        } actions: {
            Button("Start over", action: retry).buttonStyle(.borderedProminent)
        }
    }
}
