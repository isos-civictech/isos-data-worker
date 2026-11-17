# Graph Report - src  (2026-11-17)

## Corpus Check
- Corpus is ~27,304 words - fits in a single context window. You may not need a graph.

## Summary
- 1154 nodes · 2405 edges · 78 communities (27 shown, 51 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 390 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- domain/entities
- infrastructure/adapters
- api/routes
- infrastructure/adapters
- ports/repositories
- domain/entities
- application/use_cases
- infrastructure/adapters
- domain/entities
- application/use_cases
- routes/sync
- infrastructure/http
- persistence/serving
- persistence/raw
- application/use_cases
- infrastructure/adapters
- application/use_cases
- ports/sources
- infrastructure/adapters
- infrastructure/adapters
- infrastructure/adapters
- ports/repositories
- serving/mappers
- ports/projections
- serving/mappers
- infrastructure/adapters
- application/use_cases
- domain/entities
- ports/sources
- persistence/serving
- persistence/serving
- raw/mappers
- api/routes
- persistence/serving
- routes/sync
- persistence/serving
- ports/projections
- ports/projections
- ports/projections
- ports/projections
- ports/projections
- persistence/serving
- infrastructure/persistence
- infrastructure/adapters
- infrastructure/adapters
- ports/projections
- domain/entities
- persistence/raw
- persistence/raw

## God Nodes (most connected - your core abstractions)
1. `SyncReport` - 78 edges
2. `build_worker()` - 50 edges
3. `Law` - 29 edges
4. `SaveOutcome` - 26 edges
5. `Worker` - 24 edges
6. `HttpClient` - 24 edges
7. `AnDeputyAdapter` - 23 edges
8. `RawStoragePort` - 22 edges
9. `SyncAll` - 21 edges
10. `AnDebateAdapter` - 21 edges

## Surprising Connections (you probably didn't know these)
- `CollectAgenda` --uses--> `IngestionLogRepository`  [INFERRED]
  application/use_cases/collect_agenda.py → domain/ports/repositories/ingestion_log_repository.py
- `CollectAgenda` --uses--> `AgendaSource`  [INFERRED]
  application/use_cases/collect_agenda.py → domain/ports/sources/agenda_source.py
- `CollectAgenda` --uses--> `SyncReport`  [INFERRED]
  application/use_cases/collect_agenda.py → domain/shared/results.py
- `CollectAmendments` --uses--> `AmendmentRepository`  [INFERRED]
  application/use_cases/collect_amendments.py → domain/ports/repositories/amendment_repository.py
- `CollectAmendments` --uses--> `IngestionLogRepository`  [INFERRED]
  application/use_cases/collect_amendments.py → domain/ports/repositories/ingestion_log_repository.py

## Import Cycles
- None detected.

## Communities (78 total, 51 thin omitted)

### Community 0 - "domain/entities"
Cohesion: 0.05
Nodes (18): Law, LawStatus, LawType, LegislativeStage, LawRepository, LawSource, SqlRawLawRepository, law_row() (+10 more)

### Community 1 - "infrastructure/adapters"
Cohesion: 0.05
Nodes (17): Debate, DebatePoint, Intervention, DebateRepository, DebateSource, AnDebateAdapter, _in_range(), _int() (+9 more)

### Community 2 - "api/routes"
Cohesion: 0.06
Nodes (20): build_engine(), get_settings(), Settings, create_app(), lifespan(), get_engine(), get_settings_dep(), _check() (+12 more)

### Community 3 - "infrastructure/adapters"
Cohesion: 0.06
Nodes (12): AgendaItem, AgendaPoint, SittingLink, AgendaSource, AnAgendaAdapter, _datetime(), _int(), _is_sitting() (+4 more)

### Community 4 - "ports/repositories"
Cohesion: 0.05
Nodes (13): LawArticle, LawText, text_kind(), TextKind, LawTextRepository, LawTextSource, SaveOutcome, AnLawTextAdapter (+5 more)

### Community 5 - "domain/entities"
Cohesion: 0.06
Nodes (12): Amendment, AmendmentAuthorType, AmendmentStatus, AmendmentRepository, AmendmentSource, BatchOutcome, _not_blank(), SqlRawAmendmentRepository (+4 more)

### Community 6 - "application/use_cases"
Cohesion: 0.05
Nodes (3): _merge(), build_storage(), _now()

### Community 7 - "infrastructure/adapters"
Cohesion: 0.08
Nodes (12): Ballot, BallotVote, GroupVote, BallotSource, AnBallotAdapter, _as_list(), _date(), _int() (+4 more)

### Community 8 - "domain/entities"
Cohesion: 0.07
Nodes (7): SessionStatus, BallotKind, VotePosition, SessionType, SpeakerType, legislature_end(), legislature_start()

### Community 10 - "routes/sync"
Cohesion: 0.07
Nodes (7): _seen_columns(), list_runs(), summary(), law_amendments(), deputy_votes(), law_detail(), article_versions()

### Community 11 - "infrastructure/http"
Cohesion: 0.07
Nodes (5): RawStoragePort, HttpClient, _attempt(), RetryableStatus, GarageS3Storage

### Community 13 - "persistence/serving"
Cohesion: 0.14
Nodes (6): ensure_legislature(), SqlDeputyProjection, _upsert_by_external_id(), deputy_row(), mandate_row(), political_group_row()

### Community 14 - "persistence/raw"
Cohesion: 0.13
Nodes (5): PoliticalGroupRef, DeputyRepository, SqlRawDeputyRepository, _upsert(), political_group_row()

### Community 15 - "application/use_cases"
Cohesion: 0.15
Nodes (3): CollectAmendments, CollectLaws, SyncReport

### Community 18 - "application/use_cases"
Cohesion: 0.22
Nodes (10): CollectAgenda, CollectDeputies, CollectLawTexts, ProjectAmendments, SyncAll, build_worker(), Worker, AgendaRepository (+2 more)

### Community 20 - "infrastructure/adapters"
Cohesion: 0.23
Nodes (6): AnAmendmentAdapter, _date(), _datetime(), _int(), _text(), load_archive()

### Community 21 - "infrastructure/adapters"
Cohesion: 0.23
Nodes (5): _date(), _gender(), _int(), _overlaps(), _text()

### Community 24 - "serving/mappers"
Cohesion: 0.18
Nodes (3): SqlDebateProjection, debate_row(), transcript_html()

### Community 25 - "ports/projections"
Cohesion: 0.18
Nodes (3): ProjectAgenda, AgendaProjection, SqlAgendaProjection

### Community 26 - "serving/mappers"
Cohesion: 0.18
Nodes (3): debate_row_from_agenda(), sitting_slug(), sitting_title()

### Community 28 - "application/use_cases"
Cohesion: 0.24
Nodes (3): CollectBallots, BallotRepository, SqlRawBallotRepository

### Community 31 - "persistence/serving"
Cohesion: 0.24
Nodes (4): _matching_words(), deputy_slug(), slugify(), unique_slug()

### Community 32 - "persistence/serving"
Cohesion: 0.24
Nodes (3): SqlBallotProjection, ballot_row(), deputy_vote_row()

### Community 33 - "raw/mappers"
Cohesion: 0.31
Nodes (3): deputy_row(), government_role_row(), mandate_row()

### Community 34 - "api/routes"
Cohesion: 0.22
Nodes (3): health(), health_db(), home()

### Community 36 - "routes/sync"
Cohesion: 0.33
Nodes (3): agenda_today(), agenda_upcoming(), _sittings()

### Community 46 - "infrastructure/adapters"
Cohesion: 0.39
Nodes (3): _as_list(), _children(), _walk()

## Knowledge Gaps
- **51 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_worker()` connect `application/use_cases` to `domain/entities`, `infrastructure/adapters`, `api/routes`, `infrastructure/adapters`, `ports/repositories`, `domain/entities`, `application/use_cases`, `infrastructure/adapters`, `infrastructure/http`, `persistence/serving`, `persistence/raw`, `application/use_cases`, `infrastructure/adapters`, `ports/sources`, `infrastructure/adapters`, `infrastructure/adapters`, `ports/repositories`, `serving/mappers`, `ports/projections`, `application/use_cases`, `persistence/serving`, `persistence/serving`, `ports/projections`, `ports/projections`, `ports/projections`, `ports/projections`, `ports/projections`, `persistence/raw`?**
  _High betweenness centrality (0.233) - this node is a cross-community bridge._
- **Are the 34 inferred relationships involving `SyncReport` (e.g. with `CollectAgenda` and `CollectAmendments`) actually correct?**
  _`SyncReport` has 34 INFERRED edges - model-reasoned connections that need verification._
- **Should `domain/entities` be split into smaller, more focused modules?**
  _Cohesion score 0.051106639839034206 - nodes in this community are weakly interconnected._
- **Why does `SyncReport` connect `application/use_cases` to `domain/entities`, `api/routes`, `domain/entities`, `application/use_cases`, `persistence/serving`, `application/use_cases`, `ports/repositories`, `serving/mappers`, `ports/projections`, `application/use_cases`, `persistence/serving`, `persistence/serving`, `ports/projections`, `ports/projections`, `ports/projections`, `ports/projections`, `ports/projections`, `ports/projections`, `persistence/raw`, `application/use_cases`?**
  _High betweenness centrality (0.089) - this node is a cross-community bridge._
- **Are the 46 inferred relationships involving `build_worker()` (e.g. with `CollectAgenda` and `CollectAmendments`) actually correct?**
  _`build_worker()` has 46 INFERRED edges - model-reasoned connections that need verification._
- **Should `infrastructure/adapters` be split into smaller, more focused modules?**
  _Cohesion score 0.05223880597014925 - nodes in this community are weakly interconnected._
- **Why does `AnDebateAdapter` connect `infrastructure/adapters` to `domain/entities`, `infrastructure/http`, `application/use_cases`, `ports/sources`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._