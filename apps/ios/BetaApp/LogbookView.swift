import BetaKit
import Foundation
import SwiftData
import SwiftUI

@Model
final class ClimbLog {
    var date: Date
    var analysisId: String
    var betaId: String
    var grade: String?
    var moves: Int
    var summary: String

    init(beta: Beta) {
        date = .now
        analysisId = beta.analysisId
        betaId = beta.id
        grade = beta.grade
        moves = beta.moves.count
        summary = beta.summary
    }
}

struct LogbookView: View {
    @Query(sort: \ClimbLog.date, order: .reverse) private var logs: [ClimbLog]
    @Environment(\.modelContext) private var context

    var body: some View {
        NavigationStack {
            List {
                ForEach(logs) { log in
                    VStack(alignment: .leading, spacing: 4) {
                        HStack {
                            Text(log.grade ?? "—").font(.headline)
                            Text("\(log.moves) moves").foregroundStyle(.secondary)
                            Spacer()
                            Text(log.date, style: .date).font(.caption).foregroundStyle(.secondary)
                        }
                        Text(log.summary).font(.subheadline).lineLimit(2)
                    }
                }
                .onDelete { offsets in
                    for index in offsets { context.delete(logs[index]) }
                }
            }
            .overlay {
                if logs.isEmpty {
                    ContentUnavailableView(
                        "No climbs yet",
                        systemImage: "figure.climbing",
                        description: Text("Every beta you get shows up here.")
                    )
                }
            }
            .navigationTitle("Logbook")
        }
    }
}
