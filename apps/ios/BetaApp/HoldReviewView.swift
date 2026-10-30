import BetaKit
import SwiftUI

/// Confirm which detected holds are the problem: pick a colour, tap to add/remove, mark start and top.
struct HoldReviewView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        let session = model.session
        if let analysis = session.analysis, let selection = session.selection {
            VStack(spacing: 12) {
                GeometryReader { geo in
                    let imageSize = CGSize(width: analysis.imageWidth, height: analysis.imageHeight)
                    let fit = aspectFit(imageSize, in: geo.size)
                    let scale = fit.width / imageSize.width
                    ZStack(alignment: .topLeading) {
                        AsyncImage(url: analysis.imageUrl) { image in
                            image.resizable().scaledToFit()
                        } placeholder: {
                            ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
                        }
                        HoldOverlay(selection: selection, scale: scale)
                            .allowsHitTesting(false)
                    }
                    .frame(width: fit.width, height: fit.height)
                    .contentShape(Rectangle())
                    .onTapGesture(coordinateSpace: .local) { location in
                        if let hold = selection.hold(atX: location.x / scale, y: location.y / scale) {
                            session.selection?.tap(holdId: hold.id)
                        }
                    }
                    .position(x: geo.size.width / 2, y: geo.size.height / 2)
                }

                Picker("Tap to", selection: Binding(
                    get: { selection.mode },
                    set: { session.selection?.mode = $0 }
                )) {
                    Text("Add / remove").tag(HoldSelection.Mode.pick)
                    Text("Start").tag(HoldSelection.Mode.start)
                    Text("Top").tag(HoldSelection.Mode.top)
                }
                .pickerStyle(.segmented)

                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 12) {
                        ForEach(selection.colors, id: \.self) { color in
                            Button {
                                session.selection?.selectColor(color)
                            } label: {
                                Circle()
                                    .fill(Color.hold(color))
                                    .frame(width: 34, height: 34)
                                    .overlay(Circle().stroke(Color.chalk, lineWidth: 2))
                            }
                            .accessibilityLabel("\(color) holds")
                        }
                    }
                    .padding(.horizontal, 4)
                }

                if let message = session.message {
                    Text(message).font(.footnote).foregroundStyle(Color.accentOrange)
                }

                Button {
                    Task { await session.confirmProblem(profile: model.profile) }
                } label: {
                    Text("Get the beta").frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .disabled(!selection.isComplete)
            }
            .padding()
        }
    }
}

private struct HoldOverlay: View {
    let selection: HoldSelection
    let scale: CGFloat

    var body: some View {
        Canvas { context, _ in
            for hold in selection.holds {
                let rect = CGRect(x: hold.x * scale, y: hold.y * scale, width: hold.w * scale, height: hold.h * scale)
                    .insetBy(dx: -4, dy: -4)
                let chosen = selection.selected.contains(hold.id)
                context.stroke(
                    Path(ellipseIn: rect),
                    with: .color(chosen ? Color.chalk : Color.chalk.opacity(0.25)),
                    lineWidth: chosen ? 3 : 1
                )
                let label: String? = hold.id == selection.topId ? "TOP" : (selection.startIds.contains(hold.id) ? "S" : nil)
                if let label {
                    context.draw(
                        Text(label).font(.caption.bold()).foregroundStyle(Color.ink),
                        at: CGPoint(x: rect.midX, y: rect.minY - 10)
                    )
                }
            }
        }
    }
}
