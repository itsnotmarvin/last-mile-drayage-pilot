import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const inputPath = path.join(projectRoot, "data/processed/regulatory_nodes.json");
const metadataPath = path.join(projectRoot, "data/metadata.json");
const archivePath = path.join(
  projectRoot,
  "data/archive/regulatory_nodes_expanded_243_2026-07-27.json",
);
const dryRun = process.argv.includes("--dry-run");

const currentCatalog = JSON.parse(fs.readFileSync(inputPath, "utf8"));
const input =
  currentCatalog.schema_version === "0.4-clause-consolidated" &&
  fs.existsSync(archivePath)
    ? JSON.parse(fs.readFileSync(archivePath, "utf8"))
    : currentCatalog;
const metadata = JSON.parse(fs.readFileSync(metadataPath, "utf8"));

if (!Array.isArray(input.rules)) {
  throw new Error("regulatory_nodes.json does not contain a rules array");
}

const unique = (values) => [
  ...new Set(
    values.filter(
      (value) => value !== null && value !== undefined && value !== "",
    ),
  ),
];

const asArray = (value) =>
  value === null || value === undefined ? [] : Array.isArray(value) ? value : [value];

const normalizeSpace = (value) =>
  String(value ?? "")
    .replace(/\s+/g, " ")
    .trim();

const normalizedHeading = (value) =>
  normalizeSpace(value)
    .replace(
      /,?\s+(?:printed\s+)?(?:PDF\s+)?pages?\s+\d+(?:[-–]\d+)?(?:\s*\/\s*PDF\s+pages?\s+\d+(?:[-–]\d+)?)?.*$/i,
      "",
    )
    .replace(/[.,;:]+$/g, "")
    .toLowerCase();

const firstMatch = (text, patterns) => {
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match) return normalizeSpace(match[0]).toLowerCase();
  }
  return null;
};

const primaryProvision = (rule) => {
  const section = normalizeSpace(rule.source_section);
  const sourceId = rule.source_id ?? "unknown_source";

  const citation = firstMatch(section, [
    /\b(?:33|49)\s+CFR\s+\d+\.\d+[A-Za-z]?\b/i,
    /\bN\.?J\.?A\.?C\.?\s*\d+:\d+-\d+\.\d+\b/i,
    /\bElizabeth Code\s+§{1,2}\s*\d+\.\d+\.\d+\b/i,
    /\bLaws of Union County\s+§{1,2}\s*\d+-\d+\b/i,
    /\bSubrules?\s+\d+-\d+\b/i,
    /\bUIIA\s+[A-Z]\.\d+(?:\.[a-z])?\b/i,
    /§{1,2}\s*\d+\.\d+\.\d+\b/i,
    /§{1,2}\s*\d+:\d+-\d+\.\d+\b/i,
    /§{1,2}\s*\d+-\d+\b/i,
    /§{1,2}\s*\d+\.\d+\.\d+\b/i,
    /\bChapter\s+\d+\.\d+\b/i,
    /\bOrdinance\s+(?:No\.\s*)?\d+\b/i,
  ]);

  if (citation) return `${sourceId}::provision::${citation}`;
  if (rule.shared_clause_id) {
    return `${sourceId}::clause::${normalizeSpace(rule.shared_clause_id).toLowerCase()}`;
  }
  return `${sourceId}::section::${normalizedHeading(section)}`;
};

const grouped = new Map();
for (const rule of input.rules) {
  const key = primaryProvision(rule);
  if (!grouped.has(key)) grouped.set(key, []);
  grouped.get(key).push(rule);
}

const metadataBySourceId = new Map(
  asArray(metadata.sources).map((source) => [source.source_id, source]),
);

const sourceGroups = new Map();
for (const rule of input.rules) {
  if (!sourceGroups.has(rule.source_id)) sourceGroups.set(rule.source_id, []);
  sourceGroups.get(rule.source_id).push(rule);
}

const sources = [...sourceGroups.entries()].map(([sourceId, rules]) => {
  const meta = metadataBySourceId.get(sourceId) ?? {};
  const provenance = rules.flatMap((rule) => asArray(rule.provenance));
  const localPaths = unique([
    meta.local_path,
    ...asArray(meta.archive_files).map((item) => item?.local_path),
    ...rules.map((rule) => rule.legacy_extraction_fields?.local_path),
  ]);

  const source = {
    source_id: sourceId,
    title:
      meta.official_title ??
      meta.title ??
      rules[0]?.source_doc ??
      provenance[0]?.title ??
      sourceId,
    issuing_authority:
      meta.issuing_authority ??
      meta.publisher ??
      rules[0]?.authority ??
      provenance[0]?.issuing_authority ??
      null,
    jurisdiction: meta.jurisdiction ?? rules[0]?.jurisdiction ?? null,
    url: meta.original_url ?? rules[0]?.source_url ?? null,
    local_paths: localPaths,
    official_status: meta.official_status ?? null,
    currentness_status:
      meta.currentness_verification_status ??
      unique(rules.map((rule) => rule.currentness_status))[0] ??
      null,
    retrieval_timestamps: unique([
      meta.retrieval_timestamp,
      ...provenance.map((item) => item?.retrieval_timestamp),
      ...rules.map((rule) => rule.temporal_evidence?.retrieval_timestamp),
    ]),
  };

  return Object.fromEntries(
    Object.entries(source).filter(
      ([, value]) => value !== null && !(Array.isArray(value) && value.length === 0),
    ),
  );
});

const requirementRecord = (rule) => {
  const requirement = {
    requirement_id: rule.rule_id,
    name: rule.rule_name,
    statement: rule.proposition ?? rule.rule_summary,
    modality: rule.modality,
    activation_conditions: asArray(rule.activation_conditions),
    exceptions: asArray(rule.exceptions),
    structured_values: asArray(rule.structured_values),
  };
  return Object.fromEntries(
    Object.entries(requirement).filter(
      ([, value]) =>
        value !== null &&
        value !== undefined &&
        value !== "" &&
        !(Array.isArray(value) && value.length === 0),
    ),
  );
};

const chooseDefinition = (rules) => {
  const statements = unique(
    rules.map((rule) => normalizeSpace(rule.proposition ?? rule.rule_summary)),
  );
  const nonRedundant = statements.filter((statement, index) => {
    const lower = statement.toLowerCase();
    return !statements.some(
      (other, otherIndex) =>
        otherIndex !== index &&
        other.length > statement.length &&
        other.toLowerCase().includes(lower),
    );
  });
  return nonRedundant.join(" ");
};

const consolidatedRules = [...grouped.values()].map((rules) => {
  const primary = rules[0];
  const requirements = rules.map(requirementRecord);
  const rule = {
    rule_id: primary.rule_id,
    rule_name: primary.rule_name,
    definition: chooseDefinition(rules),
    source_id: primary.source_id,
    source_sections: unique(rules.map((item) => item.source_section)),
    requirement_count: requirements.length,
    requirement_ids: requirements.map((item) => item.requirement_id),
    research_scope_tags: unique(
      rules.flatMap((item) => asArray(item.research_scope_tags)),
    ),
  };

  if (requirements.length === 1) {
    const only = requirements[0];
    rule.activation_conditions = only.activation_conditions ?? [];
    rule.exceptions = only.exceptions ?? [];
    if (only.structured_values) rule.structured_values = only.structured_values;
  }

  return Object.fromEntries(
    Object.entries(rule).filter(
      ([, value]) =>
        value !== null &&
        value !== undefined &&
        value !== "" &&
        !(Array.isArray(value) && value.length === 0),
    ),
  );
});

const requirementToRuleIndex = Object.fromEntries(
  consolidatedRules.flatMap((rule) =>
    rule.requirement_ids
      .filter((requirementId) => requirementId !== rule.rule_id)
      .map((requirementId) => [requirementId, rule.rule_id]),
  ),
);

const output = {
  schema_version: "0.4-clause-consolidated",
  description:
    "Clause-level regulatory catalog for the APM Terminals Elizabeth last-mile drayage pilot. Repeated source metadata is normalized into the source_registry, and related atomic requirements are nested under one regulatory rule.",
  status:
    "source-grounded evidence catalog; legal applicability, precedence, conflict, and route feasibility remain separate analytical questions",
  scope: {
    geographic:
      "Public approaches and terminal-related evidence for APM Terminals Elizabeth within Elizabeth, Union County, New Jersey.",
    node_grain:
      "One regulatory node per cited legal provision, shared source clause, or operational source section.",
    definition_policy:
      "Every regulatory node includes a plain, source-grounded definition assembled from the retained proposition or related propositions.",
    consolidation_policy:
      "Requirements from the same primary legal provision or shared source clause are retained as nested requirements instead of separate graph nodes.",
  },
  source_registry: sources,
  source_count: sources.length,
  unique_source_url_count: unique(sources.map((source) => source.url)).length,
  rules: consolidatedRules,
  rule_count: consolidatedRules.length,
  nested_requirement_count: input.rules.length,
  requirement_to_rule_index: requirementToRuleIndex,
  consolidation_summary: {
    prior_atomic_rule_count: input.rules.length,
    consolidated_rule_count: consolidatedRules.length,
    nodes_removed: input.rules.length - consolidatedRules.length,
    reduction_percent: Number(
      (
        ((input.rules.length - consolidatedRules.length) / input.rules.length) *
        100
      ).toFixed(1),
    ),
    source_url_occurrences_before: input.rules.filter((rule) => rule.source_url).length,
    source_url_occurrences_after: sources.filter((source) => source.url).length,
  },
};

const report = {
  prior_rules: input.rules.length,
  consolidated_rules: consolidatedRules.length,
  nested_requirements: input.rules.length,
  sources: sources.length,
  unique_source_urls: output.unique_source_url_count,
  nodes_removed: output.consolidation_summary.nodes_removed,
  reduction_percent: output.consolidation_summary.reduction_percent,
  rules_missing_definitions: consolidatedRules.filter(
    (rule) => !normalizeSpace(rule.definition),
  ).length,
};

if (dryRun) {
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
} else {
  fs.mkdirSync(path.dirname(archivePath), { recursive: true });
  if (!fs.existsSync(archivePath)) {
    fs.copyFileSync(inputPath, archivePath);
  }
  fs.writeFileSync(inputPath, `${JSON.stringify(output, null, 2)}\n`);
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
}
