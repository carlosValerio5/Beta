import SwiftUI

struct RootView: View {
    var body: some View {
        TabView {
            Tab("Climb", systemImage: "figure.climbing") {
                ClimbFlowView()
            }
            Tab("Logbook", systemImage: "book.closed") {
                LogbookView()
            }
            Tab("Profile", systemImage: "person.crop.circle") {
                ProfileView()
            }
        }
    }
}
