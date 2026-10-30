/** Screen-space overlay: brand, move counter, captions, callouts, slow-mo badge, outro. */
import { ACCENT, CHALK, FONT, INK, LIMB_COLORS } from "../palette";
import type { MotionSpec } from "../spec";
import { chapterAt, clamp01, fadeEnvelope, segmentAt, type Transform, toScreen } from "../timeline";

type Props = { spec: MotionSpec; frame: number; transform: Transform };

export const Hud: React.FC<Props> = ({ spec, frame, transform }) => {
  const { index } = segmentAt(spec, frame);
  const keyframe = spec.keyframes[index];
  if (!keyframe) return null;
  const chapter = chapterAt(spec, frame);
  const total = spec.chapters.length;
  const lastEnd =
    (spec.keyframes.at(-1)?.start_frame ?? 0) + (spec.keyframes.at(-1)?.duration_frames ?? 0);
  const outro = clamp01((frame - lastEnd) / 10);
  const visible = fadeEnvelope(frame, keyframe.start_frame, keyframe.duration_frames, 6, 4);
  const caption = keyframe.annotations.find((a) => a.kind === "caption");
  const callout = keyframe.annotations.find((a) => a.kind === "callout");
  const holds = new Map(spec.holds.map((h) => [h.id, h]));
  const calloutHold =
    callout?.kind === "callout" && callout.hold_id !== null
      ? holds.get(callout.hold_id)
      : undefined;
  const unit = spec.meta.width / 1080;
  const anchor = calloutHold ? toScreen(calloutHold.center, transform) : null;
  // Keep the callout inside the safe area: below the top bar, above the caption, on screen.
  const calloutAt = anchor && {
    x: Math.min(Math.max(anchor.x + 50 * unit, 40 * unit), spec.meta.width - 340 * unit),
    y: Math.min(Math.max(anchor.y - 70 * unit, 250 * unit), spec.meta.height - 420 * unit),
  };

  return (
    <div style={{ position: "absolute", inset: 0, fontFamily: FONT, color: CHALK }}>
      <div
        style={{
          position: "absolute",
          top: 70 * unit,
          left: 60 * unit,
          right: 60 * unit,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span style={{ fontSize: 44 * unit, fontWeight: 900, letterSpacing: 6 * unit }}>BETA</span>
        {chapter && (
          <span
            style={{
              background: "rgba(15,17,21,0.75)",
              padding: `${12 * unit}px ${24 * unit}px`,
              borderRadius: 999,
              fontSize: 34 * unit,
              fontWeight: 600,
              borderLeft: `${10 * unit}px solid ${keyframe.limb ? LIMB_COLORS[keyframe.limb] : ACCENT}`,
            }}
          >
            {chapter.move_index + 1}/{total} · {chapter.title.replace(/^\d+\.\s*/, "")}
          </span>
        )}
      </div>

      <div
        style={{
          position: "absolute",
          top: 150 * unit,
          left: 60 * unit,
          right: 60 * unit,
          display: "flex",
          gap: 8 * unit,
        }}
      >
        {spec.chapters.map((c) => (
          <div
            key={c.move_index}
            style={{
              flex: 1,
              height: 8 * unit,
              borderRadius: 4 * unit,
              background:
                chapter && c.move_index <= chapter.move_index ? ACCENT : "rgba(245,243,238,0.25)",
            }}
          />
        ))}
      </div>

      {keyframe.slow_motion && (
        <div
          style={{
            position: "absolute",
            top: 190 * unit,
            left: 60 * unit,
            background: ACCENT,
            color: INK,
            fontWeight: 800,
            fontSize: 30 * unit,
            padding: `${8 * unit}px ${18 * unit}px`,
            borderRadius: 10 * unit,
            opacity: visible,
          }}
        >
          SLOW-MO
        </div>
      )}

      {callout?.kind === "callout" && calloutAt && (
        <div
          style={{
            position: "absolute",
            left: calloutAt.x,
            top: calloutAt.y,
            background: ACCENT,
            color: INK,
            fontWeight: 800,
            fontSize: 36 * unit,
            padding: `${10 * unit}px ${22 * unit}px`,
            borderRadius: 14 * unit,
            opacity: visible,
            whiteSpace: "nowrap",
          }}
        >
          {callout.text}
        </div>
      )}

      {caption?.kind === "caption" && (
        <div
          style={{
            position: "absolute",
            left: 60 * unit,
            right: 60 * unit,
            bottom: 170 * unit,
            display: "flex",
            justifyContent: "center",
            opacity: visible,
          }}
        >
          <div
            style={{
              background: "rgba(15,17,21,0.82)",
              borderRadius: 24 * unit,
              padding: `${26 * unit}px ${36 * unit}px`,
              fontSize: 52 * unit,
              fontWeight: 700,
              lineHeight: 1.2,
              textAlign: "center",
            }}
          >
            {caption.text}
          </div>
        </div>
      )}

      {outro > 0 && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: `rgba(15,17,21,${0.55 * outro})`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              fontSize: 120 * unit,
              fontWeight: 900,
              opacity: outro,
              transform: `scale(${0.9 + 0.1 * outro})`,
            }}
          >
            Send it.
          </div>
        </div>
      )}
    </div>
  );
};
