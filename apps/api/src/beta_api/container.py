"""Composition root: the one place that decides which adapter implements which port."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from beta_api.media import LocalMediaStore
from beta_api.renderer import RemotionHttpRenderer
from beta_api.repositories import Database, SqliteRepository
from beta_api.settings import Settings
from beta_core.domain.records import Analysis, BetaRecord, Feedback, VideoRecord
from beta_core.ports import (
    BetaPlanner,
    Clock,
    HoldClassifier,
    IdGenerator,
    MotionDirector,
    VideoRenderer,
)
from beta_core.services.analyze import AnalyzeBoulder
from beta_core.services.feedback import RecordFeedback
from beta_core.services.generate_beta import ProduceBeta, RequestBeta
from beta_core.services.generate_video import ProduceVideo, RequestVideo
from beta_core.services.select_problem import SelectProblem
from beta_core.validation import BetaValidator, MotionSpecValidator
from beta_data.bronze import BronzeWriter
from beta_data.layout import Lakehouse
from beta_llm.classifier import ClaudeHoldClassifier
from beta_llm.director import ClaudeMotionDirector
from beta_llm.heuristic import ChoreographyDirector, HeuristicBetaPlanner
from beta_llm.planner import ClaudeBetaPlanner
from beta_llm.prompts import PromptRegistry, default_prompts_dir
from beta_llm.transport import AnthropicTransport, Transport
from beta_vision.detect import ColorHoldDetector
from beta_vision.overlay import PillowMarkRenderer
from beta_vision.preprocess import PillowPreprocessor


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class UuidIds:
    def new(self, prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:20]}"


class Container:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        clock: Clock | None = None,
        ids: IdGenerator | None = None,
        transport: Transport | None = None,
        renderer: VideoRenderer | None = None,
    ) -> None:
        self.settings = settings or Settings()
        s = self.settings
        self.clock: Clock = clock or SystemClock()
        self.ids: IdGenerator = ids or UuidIds()

        db = Database(s.db_path)
        self.analyses = SqliteRepository(db, "analyses", Analysis)
        self.betas = SqliteRepository(db, "betas", BetaRecord)
        self.videos = SqliteRepository(db, "videos", VideoRecord)
        self.feedback = SqliteRepository(db, "feedback", Feedback)
        self.media = LocalMediaStore(s.media_dir)
        self.bronze = BronzeWriter(Lakehouse(s.data_dir))

        self.preprocessor = PillowPreprocessor()
        self.detector = ColorHoldDetector()
        self.marks = PillowMarkRenderer()

        if transport is None and s.anthropic_api_key is not None:
            transport = AnthropicTransport.from_api_key(s.anthropic_api_key.get_secret_value())
        self.planner: BetaPlanner
        self.director: MotionDirector
        self.classifier: HoldClassifier | None = None
        if transport is not None:
            registry = PromptRegistry(default_prompts_dir())
            self.planner = ClaudeBetaPlanner(transport, registry, model_override=s.planner_model)
            self.director = ClaudeMotionDirector(
                transport, registry, model_override=s.director_model
            )
            if s.use_hold_classifier:
                self.classifier = ClaudeHoldClassifier(
                    transport, registry, self.marks, model_override=s.classifier_model
                )
        else:
            self.planner = HeuristicBetaPlanner()
            self.director = ChoreographyDirector()

        self.renderer: VideoRenderer | None = renderer
        if renderer is None and s.renderer_url:
            self.renderer = RemotionHttpRenderer(s.renderer_url, self.media)

    # ------------------------------------------------------------------ use cases

    def analyze(self) -> AnalyzeBoulder:
        return AnalyzeBoulder(
            preprocessor=self.preprocessor,
            detector=self.detector,
            raw_sink=self.bronze,
            media=self.media,
            analyses=self.analyses,
            events=self.bronze,
            ids=self.ids,
            clock=self.clock,
            classifier=self.classifier,
        )

    def select_problem(self) -> SelectProblem:
        return SelectProblem(analyses=self.analyses, events=self.bronze, clock=self.clock)

    def request_beta(self) -> RequestBeta:
        return RequestBeta(analyses=self.analyses, betas=self.betas, ids=self.ids, clock=self.clock)

    def produce_beta(self) -> ProduceBeta:
        return ProduceBeta(
            analyses=self.analyses,
            betas=self.betas,
            media=self.media,
            marks=self.marks,
            planner=self.planner,
            validator=BetaValidator(),
            events=self.bronze,
            clock=self.clock,
        )

    def request_video(self) -> RequestVideo:
        return RequestVideo(betas=self.betas, videos=self.videos, ids=self.ids, clock=self.clock)

    def produce_video(self) -> ProduceVideo:
        return ProduceVideo(
            videos=self.videos,
            betas=self.betas,
            analyses=self.analyses,
            media=self.media,
            director=self.director,
            validator=MotionSpecValidator(),
            renderer=self.renderer,
            events=self.bronze,
            clock=self.clock,
            marks=self.marks,
        )

    def record_feedback(self) -> RecordFeedback:
        return RecordFeedback(
            betas=self.betas,
            feedback=self.feedback,
            events=self.bronze,
            ids=self.ids,
            clock=self.clock,
        )

    # ------------------------------------------------------------------ helpers

    def media_url(self, key: str | None) -> str | None:
        return f"{self.settings.public_base_url.rstrip('/')}/media/{key}" if key else None

    def describe(self) -> dict[str, object]:
        return {
            "planner": self.planner.name,
            "director": self.director.name,
            "renderer": self.renderer is not None,
        }
