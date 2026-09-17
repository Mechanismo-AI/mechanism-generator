/* Exercise the actual offline review script without network or browser dependencies.
 * Run from any directory: node tools/test_contribution_review.cjs
 */
"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const reviewPath = path.join(__dirname, "..", "src", "mechanism_generator", "contributions", "review.html");
const html = fs.readFileSync(reviewPath, "utf8");
const scripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
assert.equal(scripts.length, 2, "Review should contain only the inert bundle and its local script");
const script = scripts[1][1];
assert.ok(html.includes("connect-src 'none'"), "Review must disable network connections");
assert.ok(!/<script\b[^>]*\bsrc=/i.test(html), "Review must not load remote scripts");
assert.ok(!/<link\b[^>]*\bhref=/i.test(html), "Review must not load external stylesheets");

// Valid local bundle fixture: known values, no paths, account names, free-form logs,
// or external URLs. Tests below deliberately add hostile text only via review inputs.
const fixture = {
  schema_version: "0.1",
  kind: "local",
  core: {
    generator_version: "0.1.0a3",
    engine: "r2.5c",
    run_status: "completed",
    validation_status: "unreviewed",
    tasks: [{
      task_id: "task-0001",
      candidate_count: 2,
      path_acceptable_count: 1,
      selection_eligible_count: 1,
      engineering_acceptable_count: 0,
      selected_count: 1
    }]
  },
  task: [{task_id: "task-0001", target_values: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]}],
  candidates: [{
    task_id: "task-0001",
    items: [
      {candidate_id: "candidate-0001", model_role: "balanced", path_acceptable: true, qualification_level: "selection_acceptable"},
      {candidate_id: "candidate-0002", model_role: "path", path_acceptable: false, qualification_level: "path_unacceptable"}
    ]
  }],
  provenance: {
    engine_sha256: "1".repeat(64),
    parent_engine_sha256: "2".repeat(64),
    models: [{role: "balanced", sha256: "3".repeat(64)}, {role: "path", sha256: "4".repeat(64)}]
  },
  settings: {seed: 17, profile_matrix: "paired", strict_qualification: true}
};

const optionalSections = ["task", "candidates", "provenance", "settings"];
const permissions = ["consent-rights", "consent-public", "consent-training"];

function makeHarness(bundle = fixture, restoredPermissions = false) {
  const elements = new Map();
  const downloads = [];
  const openings = [];
  const anchors = [];
  const timers = [];

  class Element {
    constructor(tag = "div") {
      this.tag = tag;
      this.textContent = "";
      this.children = [];
      this.handlers = {};
      this.checked = false;
      this.disabled = false;
      this.hidden = false;
      this.value = "";
    }
    set innerHTML(_value) {
      throw new Error("Review must not insert untrusted HTML");
    }
    append(...children) {
      this.children.push(...children);
      for (const child of children) if (child.id) elements.set(child.id, child);
    }
    addEventListener(event, handler) {
      this.handlers[event] = handler;
    }
    click() {
      if (!this.disabled && this.handlers.click) this.handlers.click();
    }
    remove() {}
  }

  // Reflect static IDs and disabled/hidden states in the HTML being tested.
  for (const match of html.matchAll(/<([a-z][a-z0-9-]*)\b([^>]*\bid="([^"]+)"[^>]*)>/gi)) {
    const element = new Element(match[1]);
    element.id = match[3];
    element.disabled = /\bdisabled(?:\s|$|=)/.test(match[2]);
    element.hidden = /\bhidden(?:\s|$|=)/.test(match[2]);
    elements.set(element.id, element);
  }
  const document = {
    getElementById(id) {
      assert.ok(elements.has(id), "Review requested missing DOM element: " + id);
      return elements.get(id);
    },
    createElement(tag) {
      const element = new Element(tag);
      if (tag === "a") anchors.push(element);
      return element;
    },
    body: new Element("body")
  };
  const element = id => document.getElementById(id);
  element("bundle-data").textContent = typeof bundle === "string" ? bundle : JSON.stringify(bundle);
  for (const id of permissions) element(id).checked = restoredPermissions;

  class LocalURL extends URL {
    static createObjectURL(blob) {
      downloads.push(blob);
      return "blob:local-review-test-" + downloads.length;
    }
    static revokeObjectURL() {}
  }
  vm.runInNewContext(script, {
    document,
    TextEncoder,
    URL: LocalURL,
    Blob,
    window: {open(...args) { openings.push(args); }},
    setTimeout(handler, delay) { timers.push({handler, delay}); }
  }, {filename: "review.html", timeout: 5000});

  function change(id, value) {
    const target = element(id);
    const event = typeof value === "boolean" ? "change" : "input";
    if (event === "change") target.checked = value;
    else target.value = value;
    assert.equal(typeof target.handlers[event], "function", "Missing UI change handler: " + id);
    target.handlers[event]();
  }
  return {
    element, change, downloads, openings, anchors, timers,
    preview: () => JSON.parse(element("preview").textContent),
    agree: () => permissions.forEach(id => change(id, true))
  };
}

function verifyHashVectors() {
  // Isolate the production function, not a reimplementation of its algorithm.
  const begin = script.indexOf("function sha256(bytes)");
  const end = script.indexOf("function hasPermissions()", begin);
  assert.ok(begin >= 0 && end > begin, "Could not find the production hash function");
  const hash = vm.runInNewContext("(" + script.slice(begin, end).trim() + ")");
  const known = [
    ["", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"],
    ["abc", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"]
  ];
  for (const [value, expected] of known) assert.equal(hash(new TextEncoder().encode(value)), expected);
  for (const length of [1, 55, 56, 63, 64, 65, 119, 120, 127, 128, 1000, 100000]) {
    const bytes = Uint8Array.from({length}, (_, i) => i % 256);
    assert.equal(hash(bytes), crypto.createHash("sha256").update(bytes).digest("hex"));
  }
  const unicode = new TextEncoder().encode("Delta Δ · 機構 · 🌱\n");
  assert.equal(hash(unicode), crypto.createHash("sha256").update(unicode).digest("hex"));
}

async function verifyReviewFlow() {
  const ui = makeHarness(fixture, true);
  assert.equal(ui.element("error").hidden, true);
  assert.equal(ui.element("download").disabled, true);
  assert.equal(ui.element("open-issue").disabled, true);
  assert.equal(ui.downloads.length, 0);
  assert.equal(ui.openings.length, 0);
  for (const id of permissions) assert.equal(ui.element(id).checked, false, "Reopening must clear restored consent");
  assert.equal(ui.preview().kind, "submission");
  assert.deepEqual(ui.preview().core, fixture.core);
  assert.equal(ui.preview().consent.rights_confirmed, false);
  assert.equal(ui.preview().consent.public_sharing_and_training, false);
  for (const section of optionalSections) assert.deepEqual(ui.preview()[section], fixture[section]);

  // Each category can be removed independently, including every optional section.
  for (const section of optionalSections) {
    ui.change("include-" + section, false);
    assert.equal(Object.hasOwn(ui.preview(), section), false);
  }
  assert.deepEqual(Object.keys(ui.preview()).sort(), ["consent", "contributor", "core", "kind", "schema_version"]);
  assert.deepEqual(ui.preview().core, fixture.core, "Required recorded outcome must survive all exclusions");

  ui.change("pseudonym", "  Δ 機構 🌱 <img src=x onerror=alert(1)>  ");
  ui.change("application", "Example </script><script>alert('data')</script>\nSecond line — ✓");
  for (let i = 0; i < permissions.length; i++) {
    ui.change(permissions[i], true);
    assert.equal(ui.element("download").disabled, i < permissions.length - 1);
  }
  assert.equal(ui.element("open-issue").disabled, true, "Saving the reviewed file must precede the GitHub form");
  ui.element("download").click();
  assert.equal(ui.downloads.length, 1);
  assert.equal(ui.anchors[0].download, "reviewed-contribution.json");
  assert.equal(ui.element("open-issue").disabled, false);
  assert.equal(ui.openings.length, 0, "Downloading must not contact GitHub");

  const text = await ui.downloads[0].text();
  assert.equal(text, ui.element("preview").textContent, "The preview must be the exact downloaded text");
  assert.equal(ui.downloads[0].type, "application/json;charset=utf-8");
  assert.ok(text.endsWith("\n"), "The exported file includes its trailing newline in the digest");
  const digest = crypto.createHash("sha256").update(Buffer.from(await ui.downloads[0].arrayBuffer())).digest("hex");
  assert.equal(ui.element("digest").textContent, digest, "The fingerprint must match the exact UTF-8 Blob bytes");
  const exported = JSON.parse(text);
  assert.equal(exported.contributor.pseudonym, "Δ 機構 🌱 <img src=x onerror=alert(1)>");
  assert.equal(exported.contributor.application, "Example </script><script>alert('data')</script>\nSecond line — ✓");
  assert.deepEqual(exported.consent, {terms_version: "1", license: "Apache-2.0", rights_confirmed: true, public_sharing_and_training: true});
  for (const section of optionalSections) assert.equal(Object.hasOwn(exported, section), false);

  ui.element("open-issue").click();
  assert.equal(ui.openings.length, 1);
  const [opened, target, features] = ui.openings[0];
  const url = new URL(opened);
  assert.equal(url.origin, "https://github.com");
  assert.equal(url.pathname, "/Mechanismo-AI/mechanism-generator/issues/new");
  assert.deepEqual([...url.searchParams.keys()].sort(), ["bundle_digest", "template", "title"]);
  assert.equal(url.searchParams.get("template"), "contribution.yml");
  assert.equal(url.searchParams.get("title"), "Community contribution");
  assert.equal(url.searchParams.get("bundle_digest"), digest);
  assert.equal(target, "_blank");
  assert.equal(features, "noopener,noreferrer");

  // A changed narrative, restored section, or revoked consent invalidates readiness.
  ui.change("application", "Changed observation");
  assert.equal(ui.element("open-issue").disabled, true);
  ui.element("open-issue").handlers.click();
  assert.equal(ui.openings.length, 1, "Even a direct stale handler call must not open the form");
  ui.element("download").click();
  assert.equal(ui.downloads.length, 2);
  assert.equal(ui.element("open-issue").disabled, false);
  ui.change("include-task", true);
  assert.equal(ui.element("open-issue").disabled, true);
  ui.element("download").click();
  assert.deepEqual(JSON.parse(await ui.downloads[2].text()).task, fixture.task);
  ui.change("consent-training", false);
  assert.equal(ui.element("download").disabled, true);
  assert.equal(ui.element("open-issue").disabled, true);
  ui.element("download").handlers.click();
  ui.element("open-issue").handlers.click();
  assert.equal(ui.downloads.length, 3);
  assert.equal(ui.openings.length, 1);
}

async function verifyPoseReviewFlow(version = "0.2") {
  const pose = structuredClone(fixture);
  pose.schema_version = version;
  if (version === "0.4") {
    pose.core.tasks[0].crank_direction = "negative";
    pose.task[0].crank_direction = "negative";
    pose.candidates[0].items.forEach(item => { item.crank_direction = "negative"; });
    pose.settings.crank_direction = "negative";
  }
  pose.core.generator_version = "0.1.0a4";
  Object.assign(pose.core.tasks[0], {
    orientation_required: true,
    orientation_acceptable_count: 1,
    pose_acceptable_count: 1,
    path_acceptable_count: 2
  });
  Object.assign(pose.task[0], {
    target_orientations_deg: [170, -170, 390],
    orientation_tolerances_deg: [1, 5, 12],
    orientation_frame: "coupler_A_to_B"
  });
  for (const [index, item] of pose.candidates[0].items.entries()) {
    Object.assign(item, {
      orientation_required: true, orientation_frame: "coupler_A_to_B",
      path_acceptable: true, orientation_acceptable: index === 0,
      pose_acceptable: index === 0, selection_eligible: index === 0,
      engineering_acceptable: false, max_orientation_error_deg: index === 0 ? 0.5 : 20,
      qualification_level: index === 0 ? "selection_acceptable" : "path_acceptable_but_orientation_failed"
    });
    pose.task[0].target_orientations_deg.forEach((angle, targetIndex) => {
      item["target_orientation_" + (targetIndex + 1) + "_deg"] = angle;
      item["orientation_tolerance_" + (targetIndex + 1) + "_deg"] = pose.task[0].orientation_tolerances_deg[targetIndex];
    });
  }
  if (version === "0.3") {
    pose.task[0].pose_initialization = {
      method: "three_pose_dyad_v1", enabled: true, requested_samples: 4096,
      requested_seed_count: 1, attempted_samples: 4096, finite_dyads: 4096,
      within_search_bounds: 100, full_cycle_robust_crank_shortest: 20,
      branch_and_order_consistent: 15, transmission_selection_floors: 10,
      returned_seeds: 1, evaluated_seed_count: 1, refined_candidate_count: 1,
      generation_runtime_seconds: 0.01, verification_runtime_seconds: 0.1,
      refinement_runtime_seconds: 1, source_sha256: "5".repeat(64)
    };
    pose.provenance.pose_initialization_sha256 = "5".repeat(64);
    Object.assign(pose.settings, {pose_dyad_samples: 4096, pose_dyad_seed_count: 1});
    pose.candidates[0].items.forEach((item, index) => Object.assign(item, {
      model_role: "pose_geometry", portfolio_origin: index ? "pose_refined" : "pose_seed",
      proposal_source: "three_pose_dyad_v1", generator_sample_index: 73
    }));
  }
  const ui = makeHarness(pose);
  assert.equal(ui.element("error").hidden, true);
  assert.equal(ui.preview().schema_version, version);
  assert.deepEqual(ui.preview().task, pose.task);
  assert.deepEqual(ui.preview().candidates, pose.candidates);
  const stats = Object.fromEntries(ui.element("run-summary").children.map(stat =>
    [stat.children[0].textContent, stat.children[1].textContent]));
  assert.equal(stats["Tasks requiring orientation"], "1");
  assert.equal(stats["Orientation acceptable · pose tasks"], "1");
  assert.equal(stats["Position and orientation acceptable"], "1");
  assert.ok(html.includes("requested angles, angular tolerances, tool frame"));
  assert.ok(html.includes("Pose requirements appear in both Task and Candidate sections"));
  ui.change("include-task", false);
  assert.equal(Object.hasOwn(ui.preview(), "task"), false);
  assert.equal(JSON.stringify(ui.preview()).includes("requested_samples"), false);
  assert.deepEqual(ui.preview().candidates, pose.candidates, "Candidate section explicitly retains its own requested angles");
  ui.change("include-candidates", false);
  assert.deepEqual(ui.preview().core, pose.core, "Pose outcome cannot disappear when angle data is excluded");
  assert.equal(ui.preview().core.tasks[0].orientation_required, true);
  assert.equal(ui.preview().core.tasks[0].pose_acceptable_count, 1);
  assert.equal(JSON.stringify(ui.preview()).includes("target_orientations_deg"), false);
  ui.agree();
  ui.element("download").click();
  const exported = JSON.parse(await ui.downloads[0].text());
  assert.equal(exported.schema_version, version);
  assert.deepEqual(exported.core, pose.core);
  assert.equal(ui.openings.length, 0, "Pose sharing still requires the explicit GitHub step");
  if (version === "0.3") {
    ui.change("include-provenance", false);
    ui.change("include-settings", false);
    assert.equal(JSON.stringify(ui.preview()).includes("three_pose_dyad_v1"), false);
    assert.equal(JSON.stringify(ui.preview()).includes("pose_initialization"), false);
    assert.deepEqual(ui.preview().core, pose.core);
  }
}

function verifyInvalidInput() {
  for (const malformed of ["invalid json", {schema_version: "999", kind: "local", core: fixture.core}, {schema_version: "0.1", kind: "submission", core: fixture.core}]) {
    const ui = makeHarness(malformed);
    assert.equal(ui.element("error").hidden, false);
    assert.equal(ui.element("review-content").hidden, true);
    assert.equal(ui.element("download").disabled, true);
    assert.equal(ui.element("open-issue").disabled, true);
    assert.equal(ui.downloads.length, 0);
    assert.equal(ui.openings.length, 0);
  }
  const ui = makeHarness({schema_version: "0.1", kind: "local", core: fixture.core});
  assert.equal(ui.element("error").hidden, true);
  assert.ok(ui.element("section-choices").textContent.includes("required outcome"));
}

async function verifyPanelReviewFlow() {
  const local = structuredClone(fixture);
  local.schema_version = "0.5";
  Object.assign(local.core.tasks[0], {panel_required: true, panel_acceptable_count: 1, crank_direction: "negative"});
  local.task[0].panel = {method: "sampled_full_cycle_panel_v1", bounds: [0,400,0,300],
    carrier_size: [50,10], pivot_clearance: 10, steps: 7201, carrier_frame: "coupler_A_to_B"};
  local.task[0].pose_initialization = {method: "three_pose_dyad_v2", nominal_samples: 4096, tolerance_samples: 262144};
  local.candidates[0].items.forEach((item, index) => Object.assign(item, {
    panel_required: true, panel_acceptable: index === 0, panel_steps: 7201,
    panel_x_max: 400, carrier_width: 50, proposal_source: "three_pose_tolerance_dyad_v1"
  }));
  const ui = makeHarness(local);
  assert.equal(ui.element("error").hidden, true);
  assert.deepEqual(ui.preview().task, local.task);
  const stats = Object.fromEntries(ui.element("run-summary").children.map(stat => [stat.children[0].textContent,stat.children[1].textContent]));
  assert.equal(stats["Sampled panel screen passed"], "1");
  ui.change("include-task", false);
  assert.deepEqual(ui.preview().candidates, local.candidates, "Candidate geometry retains its own panel requirements");
  ui.change("include-candidates", false);
  assert.deepEqual(ui.preview().core, local.core, "Panel outcome remains when dimensions are excluded");
  assert.equal(JSON.stringify(ui.preview()).includes("carrier_width"), false);
  ui.agree();
  ui.element("download").click();
  assert.deepEqual(JSON.parse(await ui.downloads[0].text()).core, local.core);
  assert.equal(ui.openings.length, 0);
}

(async () => {
  verifyHashVectors();
  await verifyReviewFlow();
  await verifyPoseReviewFlow();
  await verifyPoseReviewFlow("0.3");
  await verifyPoseReviewFlow("0.4");
  await verifyPanelReviewFlow();
  verifyInvalidInput();
  console.log("Offline contribution review checks passed: schemas 0.1/0.2/0.3/0.4/0.5, panel constraints and counts, crank direction, pose and geometric provenance retention, diagnostics exclusions, digest vectors, consent gates, all section exclusions, Unicode and hostile text, exact download, fixed GitHub URL, changed-file re-export, and invalid-input handling.");
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
