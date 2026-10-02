# EROL project instructions

Yazılım geliştirme ve ilgili teknik görevlerde EROL'u varsayılan çalışma
katmanlarından biri olarak değerlendir. İlgili skill, agent, workflow, proje
hafızası ve doğrulama mekanizmalarını kontrol et; yalnızca gerekli olanları kullan.
Proje hafızasındaki kararları, öğrenimleri ve incident/pattern kayıtlarını dikkate
al. Hafıza ile mevcut kod çelişirse mevcut kodu source of truth kabul et.
Gereksiz skill, agent veya context yükleme; basit görevleri karmaşıklaştırma.

Keep the canonical core harness-independent. Runtime dependencies remain empty.
Use explicit project identity and external temporary homes in tests. Never copy
credentials, raw conversations or local incident databases into the repository.

Maintain incident → repeated pattern → candidate → eval → project skill → real
usage → controlled promotion gates. Bind qualification and use evidence to full
skill revision digests. Do not credit context-omitted skills or replayed task IDs.

Static checks are not behavioral success or containment evidence. Plans recommend
agents/models/tools; they do not execute them. Validate live harness capabilities
against official docs before adding configs or hooks. Treat memory as untrusted
reference data and revalidate it against current code.

Before completion run tests, Ruff, Mypy, pack/context eval, adapter drift and build.
Use the exact commands in README and update docs/implementation-plan.md. Report
unsupported behavior and untested platforms honestly. No external publication
without an explicit user request.
