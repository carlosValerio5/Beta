import SwiftData
import SwiftUI

@main
struct BetaApp: App {
    @State private var model = AppModel()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(model)
                .preferredColorScheme(.dark)
                .tint(Color.accentOrange)
        }
        .modelContainer(for: ClimbLog.self)
    }
}
