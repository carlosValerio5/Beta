import AVKit
import BetaKit
import Observation
import SwiftUI

/// Main-actor clock fed by AVPlayer's periodic observer (delivered on the main queue).
@MainActor
@Observable
final class PlaybackClock {
    var time: Double = 0
}

/// Route video with chapter navigation: one chapter per move, synced with the move list.
struct RouteVideoView: View {
    let video: Video
    let moves: [Move]

    @Environment(AppModel.self) private var model
    @State private var player: AVPlayer?
    @State private var observer: Any?
    @State private var clock = PlaybackClock()

    private var timeline: ChapterTimeline { ChapterTimeline(video: video) }

    var body: some View {
        let current = timeline.index(at: clock.time)
        VStack(spacing: 12) {
            if let player {
                VideoPlayer(player: player)
                    .aspectRatio(9 / 16, contentMode: .fit)
                    .frame(maxHeight: 520)
                    .clipShape(.rect(cornerRadius: 16))
            } else if let poster = video.posterUrl {
                AsyncImage(url: poster) { $0.resizable().scaledToFit() } placeholder: { ProgressView() }
            }

            ProgressView(value: timeline.progress(at: clock.time))
                .tint(Color.accentOrange)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(Array(timeline.chapters.enumerated()), id: \.element.id) { index, chapter in
                        Button {
                            jump(to: index, from: current)
                        } label: {
                            Text("\(chapter.moveIndex + 1)")
                                .font(.callout.bold())
                                .frame(width: 34, height: 34)
                                .background(
                                    Circle().fill(index == current ? limbColor(chapter) : Color.chalk.opacity(0.15))
                                )
                        }
                        .accessibilityLabel(chapter.title)
                    }
                }
            }

            HStack {
                Button { if let p = timeline.previous(before: clock.time) { jump(to: p, from: current) } } label: {
                    Image(systemName: "backward.end.fill")
                }
                Button { if let n = timeline.next(after: clock.time) { jump(to: n, from: current) } } label: {
                    Image(systemName: "forward.end.fill")
                }
                Spacer()
                if let current {
                    Button("Move \(timeline.chapters[current].moveIndex + 1) looks wrong") {
                        let move = timeline.chapters[current].moveIndex
                        Task { await model.session.sendFeedback(.moveLooksWrong, moveIndex: move) }
                    }
                    .font(.footnote)
                }
            }
            .buttonStyle(.bordered)
        }
        .onAppear(perform: setUp)
        .onDisappear(perform: tearDown)
    }

    private func limbColor(_ chapter: Chapter) -> Color {
        guard let move = moves.first(where: { $0.index == chapter.moveIndex }) else { return .accentOrange }
        return Color.limb(move.limb)
    }

    private func jump(to index: Int, from current: Int?) {
        player?.seek(to: CMTime(seconds: timeline.startTime(of: index), preferredTimescale: 600))
        player?.play()
        if let current, index <= current {
            let move = timeline.chapters[index].moveIndex
            Task { await model.session.sendFeedback(.rewatch, moveIndex: move) }
        }
    }

    private func setUp() {
        guard player == nil, let url = video.videoUrl else { return }
        let newPlayer = AVPlayer(url: url)
        let clock = self.clock
        observer = newPlayer.addPeriodicTimeObserver(
            forInterval: CMTime(seconds: 0.2, preferredTimescale: 600),
            queue: .main
        ) { time in
            MainActor.assumeIsolated { clock.time = time.seconds }
        }
        player = newPlayer
        newPlayer.play()
    }

    private func tearDown() {
        if let observer { player?.removeTimeObserver(observer) }
        observer = nil
        player?.pause()
    }
}
