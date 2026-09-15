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

(async () => {
  verifyHashVectors();
  await verifyReviewFlow();
  verifyInvalidInput();
  console.log("Offline contribution review checks passed: digest vectors, consent gates, all section exclusions, Unicode and hostile text, exact download, fixed GitHub URL, changed-file re-export, and invalid-input handling.");
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
