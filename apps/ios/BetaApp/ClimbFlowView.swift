import BetaKit
import SwiftData
import SwiftUI

/// Photo → hold review → beta (+ route video). Each phase of `ClimbSession` is one screen.
struct ClimbFlowView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.modelContext) private var context

    var body: some View {
        let session = model.session
        NavigationStack {
            Group {
                switch session.phase {
                case .idle:
                    CaptureView()
                case .uploading:
                    WorkingView(title: "Finding the holds…")
                case .selecting:
                    HoldReviewView()
                case .planning:
                    WorkingView(title: "Reading the problem…", subtitle: "Planning moves for your body")
                case .ready:
                    BetaView()
                case .failed(let message):
                    FailureView(message: message) { model.newClimb() }
                }
            }
            .navigationTitle("Beta")
            .toolbar {
                if session.phase != .idle {
                    Button("New climb") { model.newClimb() }
                }
            }
        }
        .onChange(of: session.beta?.id) {
            guard let beta = session.beta, beta.status == .ready else { return }
            context.insert(ClimbLog(beta: beta))
        }
    }
}
