// The required areas of the documentation pages (ADR-0017 section 2.1), in ONE table. The gate's page library
// (inpage.mjs) measures what a section holds; this module says what each area must hold, and run.mjs applies it.
// docs/04_views.md transcribes the table and a unit test keeps the two in step: a rule is never written twice.
//
// A "topic" is a leaf panel of a page (a tab, a sub-tab or a tab-group item) that holds sections; a page without tabs is
// one topic. A tab list inside a section belongs to that section: its panels are not topics, and what they hold counts
// for the section across every state the gate visited.
// A "dense paragraph" is a visible `<p>` of at least DENSE_WORDS words in the displayed language, equations removed,
// counted once per distinct text. Hidden elements never count.

export const DENSE_WORDS = 40;
export const LEDE_WORDS = 35;
export const REASON_MIN = 12;
export const METHOD_KINDS = ['classical', 'learned'];

/** What a rule counts in a section: the key of the measurement taken by `G.docSections` and how it reads in a message. */
export const RULES = {
  dense: { noun: 'dense paragraph(s)', min: true },
  equations: { noun: 'captioned equation(s)', min: true },
  figures: { noun: 'figure(s) with a caption', min: true },
  callouts: { noun: 'callout(s)', min: true },
  glossary: { noun: 'glossary item(s)', min: true },
  steps: { noun: 'step(s) in an ordered list', min: true },
  controls: { noun: 'control(s)', min: true },
  refs: { noun: 'reference(s) cited', min: true },
  stats: { noun: 'quantified statement(s) (value, unit, source)', min: true },
  rows: { noun: 'row(s) of capability, outcome and proof point', min: true },
  rowsNoStat: { noun: 'row(s) whose proof point is not a quantified statement', max: true },
  items: { noun: 'item(s)', exact: true },
  thinItems: { noun: 'item(s) without a sentence', max: true },
  qa: { noun: 'question and answer pair(s)', min: true },
  honest: { noun: 'honest callout(s)', exact: true },
  honestOrStrong: { noun: 'honest or strong callout(s)', exact: true },
  // derived: tables and charts are alternatives in some areas
  table: { noun: 'table(s)', min: true },
  chart: { noun: 'chart(s)', min: true },
  tableOrChart: { noun: 'table(s) or chart(s)', min: true, of: ['tables', 'charts'] },
  tableOrCode: { noun: 'table(s) or code block(s)', min: true, of: ['tables', 'codes'] },
};

const measureOf = (m, key) => {
  const r = RULES[key];
  if (r.of) return r.of.reduce((a, k) => a + (m[k] ?? 0), 0);
  if (key === 'table') return m.tables ?? 0;
  if (key === 'chart') return m.charts ?? 0;
  if (key === 'honestOrStrong') return (m.honest ?? 0) + (m.strong ?? 0);
  return m[key] ?? 0;
};

/**
 * The floors a section fails. `m` is the measurement of the section (see `G.docSections`), `rule` the area's rule
 * (`{ dense: 2, equations: 1, honest: 1 }`: a number is a minimum, or the exact count for `honest` and `honestOrStrong`).
 * @returns {string[]} one text per failed rule, with the measured number and the floor
 */
export function failedRules(m, rule) {
  const out = [];
  for (const [key, want] of Object.entries(rule)) {
    const def = RULES[key];
    if (!def) throw new Error(`gate/areas.mjs: unknown rule ${key}`);
    const n = measureOf(m, key);
    if (def.max ? n > want : def.exact ? n !== want : n < want) out.push(`${n} ${plural(def.noun, n)}, ${def.max ? `at most ${want} is allowed` : def.exact ? `exactly ${want} is required` : `the floor is ${want}`}`);
  }
  return out;
}

/** The rule as a sentence, for the docs and the gate's messages. */
export function describeRule(rule) {
  return Object.entries(rule)
    .map(([key, want]) => `${RULES[key].max ? 'at most' : RULES[key].exact ? 'exactly' : 'at least'} ${want} ${RULES[key].noun.replace('(s)', want === 1 ? '' : 's')}`)
    .join(', ');
}

const A = (en, es, requires, extra = {}) => ({ what: { en, es }, requires, ...extra });

/**
 * The five tables of ADR-0017 section 2.1. `areas`: the vocabulary of the page (name, what it is in both languages,
 * what the gate requires in a section of that area). `floors`: the page-level floors by their stable slug (`min` over
 * the topics, learned methods, figures or captioned equations the page shows, or the words of its lede).
 */
export const PAGES = {
  '/introduction': {
    name: 'Introduction',
    // two top-level topics: the executive view first (the default), then the technical view. The executive view has no
    // areas: it is the shell's ExecutiveView, checked by executiveFailures below (0.12.0, problem-context-first.md).
    views: ['executive', 'technical'],
    areas: {
      problem: A('the industrial or scientific problem, with the concrete equipment, setting and who it serves', 'el problema industrial o científico, con el equipo concreto, el contexto y a quién sirve', { dense: 2 }, { view: 'technical' }),
      principles: A('the physics or the domain principles the product rests on', 'la física o los principios del dominio en que se apoya el producto', { dense: 2 }, { view: 'technical' }),
      math: A('the governing mathematics', 'la matemática que gobierna', { equations: 1, glossary: 10 }, { view: 'technical' }),
      pipeline: A('the end-to-end pipeline, from the data to the screen', 'el flujo completo, desde los datos hasta la pantalla', { steps: 4 }, { view: 'technical' }),
      honesty: A('what is exact and what is illustrative; what the product is not', 'qué es exacto y qué es ilustrativo; qué no es el producto', { honest: 1, dense: 1 }, { view: 'technical' }),
    },
    floors: {
      'intro-figure': { what: 'at least 1 overview figure in the technical view', measure: 'figures', min: 1, noun: 'figure(s) in the technical view' },
      'intro-equations': { what: 'at least 3 captioned equations in the technical view', measure: 'equations', min: 3, noun: 'captioned equation(s) in the technical view' },
    },
  },
  '/methodology': {
    name: 'Methodology',
    areas: {
      method: A(
        'one method family, as the build runs it: its exact behaviour and constants',
        'una familia de métodos, tal como la ejecuta el producto: su comportamiento exacto y sus constantes',
        { dense: 4, equations: 2, figures: 1, honest: 1, refs: 1 },
        { perTopic: true, kinds: METHOD_KINDS },
      ),
    },
    floors: {
      'method-topics': { what: 'at least 6 topics, one per method family', measure: 'topics', min: 6, noun: 'topic(s)' },
      'method-learned': { what: 'at least 2 topics of kind learned', measure: 'learned', min: 2, noun: 'topic(s) of kind learned' },
    },
  },
  '/implementation': {
    name: 'Implementation',
    areas: {
      architecture: A('offline pipeline, compact artifacts, the thin live lane, the browser', 'el flujo offline, los artefactos compactos, el carril vivo delgado y el navegador', { figures: 1 }),
      reproducibility: A('determinism, seeds, versions, how a result is reproduced', 'determinismo, semillas, versiones, cómo se reproduce un resultado', { callouts: 1, dense: 1 }),
      engine: A('the exact algorithm steps, constants, windows and scaling of one engine', 'los pasos exactos del algoritmo, las constantes, las ventanas y la escala de un motor', { dense: 2, equations: 1, callouts: 1 }),
      lanes: A('the live and precompute boundary, and what admits a feature to the live lane', 'el límite entre lo vivo y lo precalculado, y qué admite una función en el carril vivo', { dense: 2 }),
      contract: A('the artifact and data contracts', 'los contratos de artefactos y de datos', { tableOrCode: 1, dense: 1 }),
      deployment: A('where and how it is deployed', 'dónde y cómo se despliega', { dense: 1 }),
    },
    floors: {
      'impl-topics': { what: 'at least 8 topics', measure: 'topics', min: 8, noun: 'topic(s)' },
    },
  },
  '/experiments': {
    name: 'Experiments',
    areas: {
      question: A('a distinct experimental question and its answer (one section per question)', 'una pregunta experimental distinta y su respuesta (una sección por pregunta)', { dense: 2 }),
      metrics: A('the exact metric equations with their real constants', 'las ecuaciones exactas de las métricas con sus constantes reales', { equations: 2 }),
      protocol: A('the leakage-safe, held-out protocol, with the forbidden anti-pattern shown', 'el protocolo sin fuga y con datos retenidos, con el antipatrón prohibido a la vista', { figures: 1 }),
      datasets: A('the datasets, their redistribution class and their live or roadmap status', 'los conjuntos de datos, su clase de redistribución y su estado (vivo o en hoja de ruta)', { table: 1 }),
    },
    floors: {
      'exp-topics': { what: 'at least 6 topics', measure: 'topics', min: 6, noun: 'topic(s)' },
    },
  },
  '/benchmark': {
    name: 'Benchmark',
    areas: {
      results: A('held-out numbers read from committed artifacts', 'cifras de datos retenidos, leídas de artefactos versionados', { tableOrChart: 1 }),
      comparison: A('a learned model and a classical baseline on the same real data', 'un modelo aprendido y una línea base clásica sobre los mismos datos reales', { tableOrChart: 1 }),
      robustness: A('an honest robustness or degradation curve', 'una curva honesta de robustez o degradación', { chart: 1 }),
      live: A('a live in-browser inference panel on real held-out data', 'un panel de inferencia en vivo en el navegador sobre datos reales retenidos', { controls: 1 }),
      provenance: A('per row: dataset, difficulty source, redistribution', 'por fila: conjunto de datos, fuente de la dificultad, redistribución', { table: 1 }),
      caveat: A('the honest limits of the comparison', 'los límites honestos de la comparación', { honestOrStrong: 1 }),
    },
    floors: {},
  },
};

/** Every documentation page: the lede. */
export const COMMON_FLOORS = {
  'lede-words': { what: `a lede of at least ${LEDE_WORDS} words`, measure: 'ledeWords', min: LEDE_WORDS, noun: 'word(s) in the lede' },
};

export const DOC_ROUTES = Object.keys(PAGES);

/** The floor ids a page's waiver may name: its areas, its page-level floors and the lede. */
export const waivable = (route) => [
  ...Object.entries(PAGES[route].areas).filter(([, a]) => a.view !== 'executive').map(([k]) => k),
  ...Object.keys(PAGES[route].floors),
  ...Object.keys(COMMON_FLOORS),
];
/** The executive view of the Introduction is the decision maker's page: none of its areas, and not the view, can be waived. */
export const NOT_WAIVABLE_NOTE = 'the executive view of the Introduction cannot be waived';
/** What a waiver may not name: the executive view and the four areas it replaced (0.12.0). */
export const EXECUTIVE_FLOORS = ['executive', 'executive-view', 'initiative', 'outcomes', 'positioning', 'credibility'];

// ------------------------------------------------------------------------------------------------ the executive view
// The executive view of the Introduction is the shell's ExecutiveView fed by the product's content/executive.json
// (conventions/problem-context-first.md). Its structure and its floors are `src/content/executive.schema.json`; its writing
// limits, its floors and its 4 C's are here AND in `src/content/executive.ts` (test/executive.test.ts keeps them equal): the
// gate measures the rendered page, the component validates the data.
export const EXEC_SCHEMA_VERSION = '2.0.0';
export const EXEC_LIMITS = {
  maxWords: 30,
  minParagraphWords: 25,
  equation: /\$|\\\(|\\\[|\\[a-zA-Z]+/,
  citations: [/\(\s*Source/i, /\[\d+\]/, /\(\s*ECB/, /\(\w[^()]*\d{4}\)/],
  minLabelPx: 9,
  fileCitations: [/\bfile\s*\d/i, /\barchivo\s*\d/i, /\.pdf\b/i, /\bPublished on\b/i],
  promotional: [/\bour\s+clients?\b/i, /\bnuestros?\s+clientes?\b/i, /\bcontact\s+us\b/i, /\bcontáctenos\b/i, /\bbuy\b/i, /\bcomprar\b/i, /\bprices?\b/i, /\bprecios?\b/i, /\boffers?\b/i, /\bofertas?\b/i],
};
/** The floors of the view as [min, max] counts of rows; a copy of EXEC_FLOORS of src/content/executive.ts (and of the schema's minItems and maxItems). */
export const EXEC_FLOORS = {
  headline_figures: [2, 3],
  'pain.paragraphs': [2, 3],
  'pain.bearers': [3, 5],
  'pain.figures': [2, 4],
  'pain.causes': [3, 5],
  'context.paragraphs': [1, 2],
  'context.forces': [3, 4],
  'context.evidence': [1, 4],
  'situation.roles': [3, 5],
  'situation.state_of_the_art': [3, 5],
  'trends.items': [3, 5],
  'proposal.paragraphs': [1, 2],
  'proposal.four_cs': [4, 4],
  'proposal.actions': [3, 6],
  'proposal.risks': [1, 4],
  'proposal.unknowns': [1, 4],
};
/** The sub-tab (1 to 5) each floor is shown in; 0 is the landing block, shown above the sub-tabs in every state. */
const floorTab = (key) => ({ headline_figures: 0, pain: 1, context: 2, situation: 3, trends: 4, proposal: 5 })[key.split('.')[0]];
/** The sub-tabs of the view: the shell's own titles. A copy of EXEC_SECTION_DEFS of src/content/executive.ts; test/executive.test.ts keeps the two equal. */
export const EXEC_SECTIONS = [
  { title: { en: 'The pain', es: 'El problema' } },
  { title: { en: 'The context', es: 'El contexto' } },
  { title: { en: 'The current situation', es: 'La situación actual' } },
  { title: { en: 'The trends', es: 'Las tendencias' } },
  { title: { en: 'The proposal', es: 'La propuesta' } },
];
/** What the page must never print: the rubric's four labels and four questions, in both languages (Felipe, 2026-10-13: the rubric gives ideas and language, not content). */
export const EXEC_RUBRIC_LABELS = ['Industry & Exec Tailoring', 'Industria y foco ejecutivo', 'AI Transformation Story', 'Historia de transformación con IA', '4Cs Positioning', 'Posicionamiento 4C', 'Delivery & Credibility', 'Entrega y credibilidad'];
export const EXEC_RUBRIC_QUESTIONS = ['Built for a C-suite exec?', '¿Pensado para un ejecutivo de primer nivel?', 'Outcomes, not a feature tour', 'Resultados, no un recorrido de funciones', 'Value story, not features dump', 'Historia de valor, no lista de funciones', 'Trust them in front of a CxO?', '¿Confiaría en ellos frente a un ejecutivo?'];
/** The illustrations and the sub-tab each sits in. */
export const EXEC_ILLUSTRATIONS = [
  { name: 'pain', section: 1 },
  { name: 'situation', section: 3 },
  { name: 'proposal', section: 5 },
];
/** The 4 C's with the names and definitions Felipe gave on 2026-10-13 (the same as FOUR_CS of src/content/executive.ts; test/executive.test.ts keeps them equal). */
export const EXEC_FOUR_CS = [
  { name: { en: 'Choice', es: 'Elección' }, definition: { en: 'flexibility across proprietary and open models.', es: 'flexibilidad entre modelos propietarios y abiertos.' } },
  { name: { en: 'Context', es: 'Contexto' }, definition: { en: 'AI grounded in business meaning, so decisions are accurate.', es: 'IA anclada en el significado del negocio, para que las decisiones sean exactas.' } },
  { name: { en: 'Cost', es: 'Costo' }, definition: { en: 'visibility of what the AI spends.', es: 'visibilidad de lo que gasta la IA.' } },
  { name: { en: 'Control', es: 'Control' }, definition: { en: 'one governance over data, models and agents.', es: 'una sola gobernanza sobre datos, modelos y agentes.' } },
];
/** The onward links under the sources (a copy of ONWARD_LINKS of src/content/executive.ts). */
export const EXEC_LINKS = {
  technical: { en: 'How the work explores this problem', es: 'Cómo explora el trabajo este problema' },
  app: { en: 'Open the App', es: 'Abrir la App' },
};

/** How many sentences a field of the view may hold: one for the single-sentence fields, two for the key statement, no limit otherwise. */
export const execSentenceLimit = (path) =>
  /^title$|\.key_message$|^context\.evidence\[\d+\]\.statement$|^situation\.interaction$|\.signal\.statement$|^proposal\.four_cs\[\d+\]\.applies$|^proposal\.actions\[\d+\]\.(action|check)$|^proposal\.(risks|unknowns)\[\d+\]$|^proposal\.handoff$|^illustrations\.\w+\.caption$/.test(path)
    ? 1
    : path === 'key_statement'
      ? 2
      : undefined;
/** The fewest words a field of the view may hold: a paragraph needs EXEC_LIMITS.minParagraphWords. */
export const execMinWords = (path) => (/\.paragraphs\[\d+\]$/.test(path) ? EXEC_LIMITS.minParagraphWords : undefined);

const sentencesOf = (text) =>
  text
    .split(/(?<=[.?!])\s+/)
    .map((x) => x.trim())
    .filter(Boolean);
const wordsIn = (text) => text.split(/\s+/).filter((w) => /[\p{L}\p{N}]/u.test(w)).length;

/** The problems with the title or the note of one source note (the same rules as sourceTextProblems of src/content/executive.ts). */
export function execSourceTextProblems(text, maxSentences) {
  const out = [];
  const sentences = sentencesOf(text);
  for (const sentence of sentences) {
    const n = wordsIn(sentence);
    if (n > EXEC_LIMITS.maxWords) out.push(`a sentence of ${n} words; the limit is ${EXEC_LIMITS.maxWords}`);
  }
  if (maxSentences !== undefined && sentences.length > maxSentences) out.push(maxSentences === 1 ? `must be one sentence, has ${sentences.length}` : `has ${sentences.length} sentences; the limit is ${maxSentences}`);
  const written = /https?:\/\//i.test(text);
  for (const re of EXEC_LIMITS.fileCitations) {
    if (re.source.includes('pdf') && written) continue;
    const m = re.exec(text);
    if (m) out.push(`cites a file name or number in place of the link ("${m[0]}"); give the publication as the title and its https link as the url`);
  }
  return out;
}

/**
 * The problems of the executive view in one language, from what the page showed in every state of the walk in which
 * the executive view was open (`G.docPage().executive` of gate/inpage.mjs, one entry per state, the first being the
 * state the page opened on). Pure. The five sections are sub-tabs, so one state shows one section: the sections, fields,
 * rows, illustrations and figures of the states are gathered and checked together, and a sub-tab the walk never opened is a
 * failure. An entry is null or {count: 0} when the page renders no ExecutiveView.
 * @returns {string[]} one text per problem
 */
export function executiveFailures(list, lang) {
  const L = lang.toUpperCase();
  const out = [];
  const bad = (m) => out.push(`Introduction, executive view (${L}): ${m}`);
  const states = (list ?? []).filter(Boolean);
  const first = states[0];
  if (!first || first.count === 0) {
    bad("no ExecutiveView ([data-executive-view]); the executive view is the shell's ExecutiveView fed by content/executive.json (docs/06_executive-view.md)");
    return out;
  }
  for (const facts of states) {
    if (facts.count === 0) continue;
    if (facts.count > 1) bad(`${facts.count} ExecutiveView elements; exactly 1 is required`);
    if (facts.schema !== EXEC_SCHEMA_VERSION) bad(`the view declares schema "${facts.schema ?? 'none'}", expected "${EXEC_SCHEMA_VERSION}"`);
    if (facts.valid !== 'true') {
      bad(`the data file is not valid in the page: ${String(facts.errors || 'no reason given').slice(0, 400)}`);
      return [...new Set(out)];
    }
    if (facts.docSections > 0) bad(`${facts.docSections} DocSection(s) placed in the executive view (${facts.docSectionTitles.join(', ')}); the view has exactly its sections and takes none`);
    if (facts.strangers.length > 0) bad(`${facts.strangers.length} block(s) beside the ExecutiveView (${facts.strangers.slice(0, 3).map((x) => `"${x}"`).join(', ')}); the view is the whole of the executive view`);
    if (!facts.inOpenView) bad('the ExecutiveView is not in the open executive view');
  }

  // the landing block above the sub-tabs: the title, the key statement, two or three headline figures
  const landing = first.landing;
  if (!landing || !landing.present) bad('no landing block above the sub-tabs (the title, the key statement and the headline figures)');
  else {
    if (!landing.title) bad('the landing block has no title');
    if (!landing.statement) bad('the landing block has no key statement');
  }

  // the sections are the sub-tabs, in order, the first selected, one section shown at a time
  const tabs = first.tabs ?? [];
  if (tabs.length === 0) bad('the sections are not sub-tabs: the view has no sub-tab list; the sections must be the sub-tabs of SubTabs, one per section (shell 0.13.0)');
  else {
    if (tabs.length !== EXEC_SECTIONS.length) bad(`the executive view shows ${tabs.length} sub-tab(s), exactly ${EXEC_SECTIONS.length} are required (one per section)`);
    EXEC_SECTIONS.forEach((def, i) => {
      if (tabs[i] !== undefined && tabs[i] !== def.title[lang]) bad(`sub-tab ${i + 1} is labelled "${tabs[i]}", expected "${def.title[lang]}"`);
    });
    if (first.activeTab !== 0) bad('the first sub-tab is not the one selected when the view opens');
  }
  for (const facts of states) {
    if (facts.count === 0) continue;
    if (facts.sections.length > 1) bad(`${facts.sections.length} sections shown at once; the view shows one section at a time, each in its own sub-tab`);
  }
  const bySection = new Map();
  for (const facts of states) {
    if (facts.count === 0) continue;
    for (const sec of facts.sections) {
      if (!bySection.has(sec.n)) bySection.set(sec.n, { sec, facts });
      if (tabs.length > 0 && facts.sections.length === 1 && facts.activeTab !== sec.n - 1) bad(`section ${sec.n} sits in sub-tab ${facts.activeTab + 1}, it belongs in sub-tab ${sec.n}`);
    }
  }
  EXEC_SECTIONS.forEach((def, i) => {
    const got = bySection.get(i + 1);
    if (!got) {
      bad(`sub-tab "${def.title[lang]}" was never visited, so its section was never checked`);
      return;
    }
    if (got.sec.title !== def.title[lang]) bad(`section ${i + 1} is titled "${got.sec.title}", expected "${def.title[lang]}"`);
    // every sub-tab opens with its key message line, which a reader can read on its own
    if (!got.sec.keyFirst) bad(`section ${i + 1} ("${def.title[lang]}") does not open with its key message line`);
    else if (!got.sec.keyMessage) bad(`section ${i + 1} ("${def.title[lang]}") has an empty key message line`);
  });
  for (const n of bySection.keys()) if (n < 1 || n > EXEC_SECTIONS.length) bad(`section ${n} is not one of the ${EXEC_SECTIONS.length} sections`);

  // the floors: the rows each part of the view shows, at least the minimum and at most the maximum
  const visited = new Set([0, ...bySection.keys()]);
  for (const [key, [min, max]] of Object.entries(EXEC_FLOORS)) {
    if (!visited.has(floorTab(key))) continue;
    const n = Math.max(0, ...states.map((x) => x.items?.[key] ?? 0));
    if (n < min) bad(`${key}: ${n} row(s) are shown, at least ${min} are required`);
    else if (n > max) bad(`${key}: ${n} row(s) are shown, at most ${max} are allowed`);
  }

  // the 4 C's of the proposal: Felipe's names and definitions, in order, each applied to the proposal
  const s5 = bySection.get(5);
  if (s5) {
    const cs = s5.facts.cs ?? [];
    if (cs.length !== 4) bad(`the proposal holds ${cs.length} row(s) of the 4 C's, exactly 4 are required`);
    EXEC_FOUR_CS.forEach((c, i) => {
      const got = cs[i];
      if (!got) return;
      if (got.name !== c.name[lang]) bad(`C ${i + 1} is named "${got.name}", expected "${c.name[lang]}" (the 4 C's in Felipe's order: ${EXEC_FOUR_CS.map((x) => x.name[lang]).join(', ')})`);
      else if (got.def !== c.definition[lang]) bad(`C ${i + 1} ("${c.name[lang]}") defines itself as "${got.def}", expected "${c.definition[lang]}"`);
      else if (!got.applies) bad(`C ${i + 1} ("${c.name[lang]}") says nothing about what it means for the proposal`);
    });
  }

  // the view takes the full width of the document column (its illustrations may stay centred inside their figure)
  const narrow = new Set();
  let column = 0;
  for (const facts of states) {
    column = Math.max(column, facts.column ?? 0);
    for (const x of facts.narrow ?? []) narrow.add(x);
  }
  if (narrow.size > 0) bad(`${narrow.size} block(s) narrower than the ${column}px document column: ${[...narrow].slice(0, 4).join(', ')}; the executive view takes the full width of the column`);

  // the rubric's labels and questions are never printed on the page
  const printed = new Map();
  for (const facts of states) {
    const text = String(facts.text ?? '').toLowerCase();
    for (const [kind, names] of [['label', EXEC_RUBRIC_LABELS], ['question', EXEC_RUBRIC_QUESTIONS]]) for (const x of names) if (text.includes(x.toLowerCase())) printed.set(x, kind);
  }
  for (const [x, kind] of printed) bad(`prints the rubric's ${kind} "${x}"; the rubric gives the ideas and the language, not the content (docs/06_executive-view.md)`);

  // the writing limits, on the text a reader sees, across every sub-tab
  const fields = new Map();
  for (const facts of states) for (const f of facts.fields ?? []) fields.set(`${f.path}|${f.text}`, f);
  const unreadable = [];
  for (const f of fields.values()) {
    if (!f.readable) {
      unreadable.push(f.path);
      continue;
    }
    const sentences = sentencesOf(f.text);
    for (const sentence of sentences) {
      const n = wordsIn(sentence);
      if (n > EXEC_LIMITS.maxWords) bad(`field "${f.path}": a sentence of ${n} words; the limit is ${EXEC_LIMITS.maxWords}`);
    }
    const max = execSentenceLimit(f.path);
    if (max !== undefined && sentences.length > max) bad(`field "${f.path}": ${sentences.length} sentences; the limit is ${max}`);
    const min = execMinWords(f.path);
    if (min !== undefined && wordsIn(f.text) < min) bad(`field "${f.path}": ${wordsIn(f.text)} words; a paragraph needs at least ${min}`);
    if (EXEC_LIMITS.equation.test(f.text)) bad(`field "${f.path}": holds an equation or a TeX marker`);
    if (EXEC_LIMITS.citations.some((re) => re.test(f.text))) bad(`field "${f.path}": holds an inline citation (sources are numbered notes)`);
    for (const re of EXEC_LIMITS.promotional) {
      const m = re.exec(f.text);
      if (m) bad(`field "${f.path}": holds promotional or client-bound wording ("${m[0]}"); the executive view is general, never a client, never a pitch`);
    }
  }
  if (unreadable.length > 0) bad(`${unreadable.length} field(s) are in the page and a reader cannot read them: ${[...new Set(unreadable)].slice(0, 4).join(', ')}`);

  // the source notes: always there, one per source cited, each a title that links to an https url, with a note that cites no file
  const cited = new Set(states.flatMap((x) => x.cites ?? []));
  for (const facts of states) {
    const notes = facts.notes ?? [];
    if (notes.length !== cited.size) bad(`${notes.length} source note(s) for ${cited.size} source(s) cited`);
    notes.forEach((n, i) => {
      const at = `source note ${i + 1}`;
      if (!n.href || !n.title) {
        bad(`${at} has no link: a source is its title linked to an https:// url (docs/06_executive-view.md)`);
        return;
      }
      if (!/^https:\/\/\S+$/.test(n.href)) bad(`${at} links to "${n.href}"; a source is an https:// link`);
      for (const [what, text, max] of [['title', n.title, undefined], ['note', n.note, 1]]) {
        if (!text) continue;
        for (const m of execSourceTextProblems(text, max)) bad(`${at}: the ${what} ${m}`);
      }
    });
  }

  // the two onward links under the sources, worded as destinations
  const links = first.links ?? [];
  for (const kind of ['technical', 'app']) {
    const got = links.find((x) => x.kind === kind);
    if (!got) bad(`no onward link to ${kind === 'app' ? 'the App' : 'the technical view'} under the sources`);
    else if (got.text !== EXEC_LINKS[kind][lang]) bad(`the onward link to ${kind === 'app' ? 'the App' : 'the technical view'} reads "${got.text}", expected "${EXEC_LINKS[kind][lang]}"`);
    else if (kind === 'app' && !/\/app\/?(\?|#|$)/.test(got.href ?? '')) bad(`the onward link to the App goes to "${got.href}", not to the App route`);
  }

  // the three illustrations, in their places
  const seen = new Map();
  for (const facts of states) for (const ill of facts.illustrations ?? []) if (!seen.has(ill.name)) seen.set(ill.name, ill);
  const names = [...seen.keys()];
  const expected = EXEC_ILLUSTRATIONS.map((x) => x.name);
  if (names.slice().sort().join() !== expected.slice().sort().join()) bad(`the illustrations are [${names.join(', ')}], expected [${expected.join(', ')}]`);
  for (const ill of seen.values()) {
    const want = EXEC_ILLUSTRATIONS.find((x) => x.name === ill.name);
    const name = `illustration "${ill.name}"`;
    if (want && ill.section !== want.section) bad(`${name} sits in section ${ill.section}, it belongs in section ${want.section}`);
    if (ill.state === 'error') {
      bad(`${name}: the file "${ill.file}" did not load (${ill.why})`);
      continue;
    }
    if (!ill.svg) bad(`${name} is not an inline SVG`);
    if (ill.img > 0) bad(`${name} is drawn through an img tag; it must be inline so it reads the theme`);
    if (ill.chart > 0) bad(`${name} declares a chart (data-chart); the executive illustrations are drawings, not charts`);
    if (ill.literal.length > 0) bad(`${name} uses literal colour(s) ${ill.literal.slice(0, 4).join(', ')}; colour only with var(--...) theme tokens, none or currentColor`);
    if (ill.outside.length > 0) bad(`${name}: label(s) outside the viewBox: ${ill.outside.slice(0, 3).map((x) => `"${x}"`).join(', ')}`);
    if (ill.labels === 0) bad(`${name} carries no label in this language`);
    if (ill.small.length > 0) bad(`${name}: label(s) smaller than ${EXEC_LIMITS.minLabelPx}px as rendered: ${ill.small.slice(0, 3).join(', ')}`);
    if (!ill.caption) bad(`${name} has no caption under it`);
  }
  return [...new Set(out)];
}

/** Parses `data-floor-waiver` ("floor: reason; floor: reason") into entries. */
export function parseWaivers(attr) {
  return String(attr ?? '')
    .split(';')
    .map((x) => x.trim())
    .filter(Boolean)
    .map((x) => {
      const i = x.indexOf(':');
      return i < 0 ? { floor: x, reason: '' } : { floor: x.slice(0, i).trim(), reason: x.slice(i + 1).trim() };
    });
}

const plural = (noun, n) => noun.replaceAll('(s)', n === 1 ? '' : 's');

/** What a waiver's reason holds that a reader can read: letters and digits, and the words that carry one (as the unavailable reason is judged). */
export const reasonStats = (reason) => ({
  chars: reason.replace(/[^\p{L}\p{N}]+/gu, '').length,
  words: reason.split(/\s+/).filter((w) => /[\p{L}\p{N}]/u.test(w)).length,
});
export const REASON_WORDS = 2;
const reasonOk = (reason) => {
  const s = reasonStats(reason);
  return s.chars >= REASON_MIN && s.words >= REASON_WORDS;
};

/** Sets of distinct things a section holds: seen again in another state they count once (a sub-tab shows others). */
const SET_KEYS = { dense: 'denseKeys', equations: 'equationKeys', figures: 'figureKeys', callouts: 'calloutKeys', honest: 'honestKeys', strong: 'strongKeys' };

/**
 * One section seen in several states (the sub-tabs of a section show different parts of it): the union of what is
 * distinct (dense paragraphs, equations, figures, callouts), the maximum of every other count. A fact without the
 * distinct keys falls back to the maximum.
 */
export function mergeSections(list) {
  const out = { ...list[0] };
  for (const key of Object.keys(list[0])) if (typeof list[0][key] === 'number') out[key] = Math.max(...list.map((s) => s[key] ?? 0));
  for (const [key, keys] of Object.entries(SET_KEYS)) {
    if (list.every((s) => Array.isArray(s[keys]))) out[key] = new Set(list.flatMap((s) => s[keys])).size;
  }
  return out;
}

/**
 * Applies the table to what a documentation page showed across its visited states (`G.docPage` of gate/inpage.mjs, one
 * entry per state) in one language. Pure: the runner passes the facts, this returns the failures and the waivers.
 * @param {{ route: string, lang: string, states: object[], expectedTopics: number }} o
 * @returns {{ failures: { trail: string, message: string }[], waivers: { floor: string, reason: string, valid: boolean }[], topics: number }}
 */
export function docFloorFailures({ route, lang, states, expectedTopics }) {
  const P = PAGES[route];
  const L = lang.toUpperCase();
  const failures = [];
  const bad = (trail, message) => failures.push({ trail, message });
  const first = states[0];
  if (!P || !first) return { failures, waivers: [], topics: 0 };
  const NAME = P.name;

  // ---- the waivers: parsed, validated, and applied only when valid
  const entries = parseWaivers(first.waiver);
  const ok = new Set(waivable(route));
  const waivers = entries.map((w) => ({ ...w, valid: ok.has(w.floor) && reasonOk(w.reason) }));
  for (const w of entries) {
    if (!ok.has(w.floor)) {
      const exec = route === '/introduction' && EXECUTIVE_FLOORS.includes(w.floor);
      bad('', `${NAME} (${L}): the waiver for "${w.floor}" is refused: ${exec ? NOT_WAIVABLE_NOTE : `it names no floor of this page (${[...ok].join(', ')})`}`);
    } else if (!reasonOk(w.reason)) {
      const s = reasonStats(w.reason);
      bad('', `${NAME} (${L}): the waiver for "${w.floor}" has a reason of ${w.reason.length} character(s) (${s.chars} letter(s) or digit(s) in ${s.words} word(s)), the floor is ${REASON_MIN} letters or digits in ${REASON_WORDS} words`);
    }
  }
  const waived = new Set(waivers.filter((w) => w.valid).map((w) => w.floor));

  // ---- the topics and the sections, gathered across the states (a section seen twice counts once)
  const topics = new Map();
  const sections = new Map();
  const figures = new Set();
  const equations = new Set();
  const execMessages = new Set();
  const execStates = [];
  for (const st of states) {
    for (const t of st.topics) topics.set(t.key, t.label);
    const ordinal = new Map();
    for (const sec of st.sections) {
      const n = ordinal.get(sec.topicKey) ?? 0;
      ordinal.set(sec.topicKey, n + 1);
      const k = `${sec.topicKey}#${n}`;
      sections.set(k, [...(sections.get(k) ?? []), sec]);
    }
    if (st.view !== 'executive') {
      for (const f of st.figures) figures.add(`${st.topics.map((t) => t.key).join('|')}::${f}`);
      for (const e of st.equations) equations.add(`${st.topics.map((t) => t.key).join('|')}::${e}`);
    }
    if (route === '/introduction' && st.view !== 'executive' && st.executive && st.executive.count > 0) {
      bad('', `${NAME} (${L}): the ExecutiveView sits in the "${st.view ?? 'none'}" view; it belongs to the executive view`);
    }
    if (route === '/introduction' && st.view === 'executive') {
      execStates.push(st.executive);
      if (st.viewEquations > 0) bad(st.topics[0]?.label ?? '', `${NAME}, executive view (${L}): ${st.viewEquations} equation(s); the executive view holds no equation`);
      if (st.viewGlossaries > 0) bad(st.topics[0]?.label ?? '', `${NAME}, executive view (${L}): ${st.viewGlossaries} symbol glossary(ies); the executive view holds none`);
    }
  }
  if (route === '/introduction' && execStates.length > 0) for (const m of executiveFailures(execStates, lang)) execMessages.add(m);
  for (const m of execMessages) bad('', m);
  const seen = [...sections.values()].map(mergeSections);
  const tname = (label) => (label ? `topic "${label}"` : 'the page');

  if (expectedTopics > topics.size) bad('', `${NAME} (${L}): the walk visited ${topics.size} of ${expectedTopics} topics; the floors of an unvisited topic were never checked`);

  // ---- the lede
  if (first.ledeWidth > 0 && first.ledeWidth < first.columnWidth - 2) bad('', `${NAME} (${L}): the lede is ${first.ledeWidth}px wide in a ${first.columnWidth}px document column; the lede takes the full width of the column`);
  if (!waived.has('lede-words') && first.ledeWords < LEDE_WORDS) bad('', `${NAME} (${L}): the lede holds ${first.ledeWords} word(s), the floor is ${LEDE_WORDS}`);

  // ---- the Introduction's views: the executive one first
  if (route === '/introduction') {
    const v = first.views ?? [];
    if (!v.includes('executive')) bad('', `${NAME} (${L}): no executive view; the top-level topics are [${v.join(', ') || 'none'}] and the executive view must be the first (ADR-0017 2.1)`);
    else if (v[0] !== 'executive') bad('', `${NAME} (${L}): the executive view is not the first topic (the first is "${v[0]}")`);
    if (v.includes('executive') && first.view !== 'executive') bad('', `${NAME} (${L}): the executive view is not the view the page opens on (it opens on "${first.view ?? 'none'}")`);
    if (!v.includes('technical')) bad('', `${NAME} (${L}): no technical view; the top-level topics are [${v.join(', ') || 'none'}]`);
  }

  // ---- each section that declares an area
  const present = new Set();
  for (const sec of seen) {
    if (route === '/introduction' && (first.views ?? []).length > 0 && sec.view !== 'executive' && sec.view !== 'technical') {
      bad(sec.topic, `${NAME} (${L}): section "${sec.title}" sits outside the two views (the executive view and the technical view hold every section of the Introduction)`);
    }
    if (!sec.area) continue;
    const def = P.areas[sec.area];
    if (!def) {
      bad(sec.topic, `${NAME}, ${tname(sec.topic)} (${L}): section "${sec.title}" declares the unknown area "${sec.area}" (this page knows: ${Object.keys(P.areas).join(', ')})`);
      continue;
    }
    present.add(sec.area);
    if (waived.has(sec.area)) continue;
    if (def.view && (def.view === 'executive') !== (sec.view === 'executive')) {
      bad(sec.topic, `${NAME}, ${sec.area} area, ${tname(sec.topic)} (${L}): the area belongs to the ${def.view} view and sits in the ${sec.view === 'executive' ? 'executive' : 'technical'} view`);
    }
    if (def.kinds && !def.kinds.includes(sec.kind)) bad(sec.topic, `${NAME}, ${sec.area} area, ${tname(sec.topic)} (${L}): section "${sec.title}" has the kind "${sec.kind ?? 'none'}", expected ${def.kinds.join(' or ')}`);
    for (const t of failedRules(sec, def.requires)) bad(sec.topic, `${NAME}, ${sec.area} area, ${tname(sec.topic)} (${L}): ${t}`);
  }

  // ---- every area of the page is declared at least once
  for (const [name, def] of Object.entries(P.areas)) {
    if (waived.has(name) || present.has(name)) continue;
    bad('', `${NAME} (${L}): no section declares the area "${name}" (${def.what.en})`);
  }

  // ---- Methodology: one method section per topic
  if (route === '/methodology' && !waived.has('method')) {
    for (const [key, label] of topics) {
      const n = seen.filter((s) => s.topicKey === key && s.area === 'method').length;
      if (n !== 1) bad(label, `${NAME}, ${tname(label)} (${L}): ${n} method section(s), exactly 1 is required`);
    }
  }

  // ---- the page-level floors
  const kinds = new Set(seen.filter((s) => s.area === 'method' && s.kind === 'learned').map((s) => s.topicKey));
  const measured = { topics: topics.size, learned: kinds.size, figures: figures.size, equations: equations.size };
  for (const [id, f] of Object.entries(P.floors)) {
    if (waived.has(id)) continue;
    if (measured[f.measure] < f.min) bad('', `${NAME} (${L}): ${measured[f.measure]} ${plural(f.noun, measured[f.measure])}, the floor is ${f.min}`);
  }
  return { failures, waivers, topics: topics.size };
}

// ------------------------------------------------------------------------------------------ flip cards and animation
// Shell 0.14.0 (CAOS_MANAGE plans/app-shell/0-14-0-plan.md decisions 3 and 4).

/** The limits of a small card, in the interface language; a copy of FLIP_LIMITS of src/content/FlipCard.tsx (test/flipCard.test.tsx keeps them equal). */
export const FLIP_LIMITS = { title: { en: 8, es: 10 }, back: { en: 40, es: 50 } };

/** The longest an illustration may play: one play, or one cycle of a loop, with its delay, in seconds. */
export const ANIMATION_MAX_SECONDS = 10;

const seconds = (v) => {
  const m = /^\s*(\d*\.?\d+)\s*(ms|s)?\s*$/i.exec(String(v ?? ''));
  return m ? Number(m[1]) / (m[2]?.toLowerCase() === 'ms' ? 1000 : 1) : 0;
};

/**
 * What an SVG file says about its animation: `css` (keyframes or an `animation` declaration), `smil` (animate, animateTransform,
 * animateMotion, set), whether it carries a `@media (prefers-reduced-motion: reduce)` block, whether that block stops the CSS
 * animation (`animation: none` or `animation-name: none`), and the longest cycle with its longest delay, in seconds (a loop counts one
 * cycle; an indefinite or absent duration counts as zero).
 */
export function analyseSvgAnimation(text) {
  const src = String(text ?? '');
  const styles = [...src.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/gi)].map((m) => m[1]).concat([...src.matchAll(/\sstyle="([^"]*)"/gi)].map((m) => m[1]));
  const css = styles.join('\n');
  const smilEls = [...src.matchAll(/<(animate|animateTransform|animateMotion|set)\b([^>]*)>/gi)];
  const hasKeyframes = /@keyframes/i.test(css);
  const hasAnimationDecl = /(^|[;{\s])animation(-name)?\s*:\s*(?!none\b)[^;}]+/i.test(css.replace(/@media[^{]*\(prefers-reduced-motion:\s*reduce\)\s*\{[\s\S]*?\}\s*\}/gi, ''));
  const cssAnimated = hasKeyframes || hasAnimationDecl;
  const smil = smilEls.length > 0;
  const block = /@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)\s*\{([\s\S]*?\}\s*)\}/i.exec(css);
  const reducedBlock = Boolean(block);
  const neutralises = Boolean(block && /animation(-name)?\s*:\s*none/i.test(block[1]));
  let maxDur = 0;
  let maxDelay = 0;
  let maxCount = 1;
  const outsideReduced = css.replace(/@media[^{]*\(prefers-reduced-motion:\s*reduce\)\s*\{[\s\S]*?\}\s*\}/gi, '');
  // the shorthand `animation: name 8s 3s infinite`: the first time is the duration, the second the delay
  for (const m of outsideReduced.matchAll(/(?:^|[;{\s])animation\s*:\s*([^;}]+)/gi)) {
    const times = [...m[1].matchAll(/(\d*\.?\d+)(ms|s)\b/gi)].map((t) => seconds(t[0]));
    maxDur = Math.max(maxDur, times[0] ?? 0);
    maxDelay = Math.max(maxDelay, times[1] ?? 0);
    // a finite count of cycles plays that many times (infinite counts one)
    if (!/infinite/i.test(m[1])) maxCount = Math.max(maxCount, Number((/(?:^|\s)(\d*\.?\d+)(?=\s|$)/.exec(m[1].replace(/(\d*\.?\d+)(ms|s)/gi, ' ')) ?? [])[1] ?? 1));
  }
  for (const m of outsideReduced.matchAll(/(?:^|[;{\s])animation-iteration-count\s*:\s*([^;}]+)/gi)) if (!/infinite/i.test(m[1])) maxCount = Math.max(maxCount, Number(m[1].split(',')[0]) || 1);
  for (const m of outsideReduced.matchAll(/(?:^|[;{\s])animation-duration\s*:\s*([^;}]+)/gi)) maxDur = Math.max(maxDur, seconds(m[1].split(',')[0]));
  for (const m of outsideReduced.matchAll(/(?:^|[;{\s])animation-delay\s*:\s*([^;}]+)/gi)) maxDelay = Math.max(maxDelay, seconds(m[1].split(',')[0]));
  // the longest duration with the longest delay: a safe bound (the rules of the file are not matched to their elements)
  let longest = maxDur * maxCount + maxDelay;
  for (const m of smilEls) {
    const attr = (n) => new RegExp(`\\s${n}="([^"]*)"`, 'i').exec(m[2])?.[1];
    const reps = Number(attr('repeatCount')) || 1;
    longest = Math.max(longest, seconds(attr('dur')) * reps + seconds(attr('begin')));
  }
  return { animated: cssAnimated || smil, css: cssAnimated, smil, reducedBlock, neutralises, seconds: Math.round(longest * 1000) / 1000 };
}

/** The problems of one illustration's animation (empty for a still); `name` is how the page calls it. */
export function animationFailures(a, name) {
  if (!a || !a.animated) return [];
  const out = [];
  if (!a.reducedBlock) out.push(`illustration "${name}" is animated and has no @media (prefers-reduced-motion: reduce) block that shows its static final frame`);
  else if (a.css && !a.neutralises) out.push(`illustration "${name}" is animated and its reduced-motion block does not stop its CSS animation (animation: none)`);
  if (a.seconds > ANIMATION_MAX_SECONDS) out.push(`illustration "${name}" plays for ${Math.round(a.seconds)} s; the limit is ${ANIMATION_MAX_SECONDS} s`);
  return out;
}
