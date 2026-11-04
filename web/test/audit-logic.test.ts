import { describe, expect, it } from "vitest";

import {
  benjaminiHochberg,
  classify,
  evidenceMatrix,
  formatPrompt,
  isReasoningModel,
  pairedStats,
  parseAnswer,
  permuteChoices,
  type Choice,
} from "../lib/audit-logic";

const make = (ids: string[], texts?: string[]): Choice[] => ids.map((id, index) => ({ id, text: texts?.[index] ?? `text ${index}` }));
const ABCD = make(["a", "b", "c", "d"], ["54", "56", "64", "78"]);
const THIRTEEN = make("abcdefghijklm".split(""));

describe("parseAnswer (parity with tests/benchmark_integrity/test_prompting.py)", () => {
  it.each([
    [ABCD, "b", "b"],
    [ABCD, "B.", "b"],
    [ABCD, "The answer is B", "b"],
    [ABCD, "Answer: (B)", "b"],
    [ABCD, "**C**", "c"],
    [ABCD, "The correct answer is **C**.", "c"],
    [ABCD, "A is tempting, but the answer is D", "d"],
    [ABCD, "Final answer: B", "b"],
    [ABCD, "Option C: 64", "c"],
    [ABCD, "(d) 78", "d"],
    [ABCD, "a", "a"],
    [ABCD, "The answer is 56", "b"],
    [ABCD, "56", "b"],
    [ABCD, "The answer is a tricky one", null],
    [ABCD, "56 is bigger than 54", null],
    [ABCD, "I don't know", null],
    [ABCD, "", null],
    [THIRTEEN, "I think the answer is C", "c"],
    [THIRTEEN, "I", "i"],
    [make(["option_1", "option_2"]), "The answer is option_2", "option_2"],
    [make(["option_1", "option_2"]), "option_2.", "option_2"],
    [make(["1", "2", "3"]), "Answer: 3", "3"],
  ])("%#: %s", (choices, text, expected) => {
    expect(parseAnswer(text as string, choices as Choice[])).toBe(expected);
  });
});

describe("permuteChoices", () => {
  it("always moves the correct answer and keeps labels positional", () => {
    for (let index = 0; index < 200; index++) {
      for (const count of [2, 3, 4, 5]) {
        const choices = make("abcde".slice(0, count).split(""), Array.from({ length: count }, (_, i) => `t${i}`));
        const item = { id: `item-${index}`, prompt: "q", expected_output: choices[index % count]!.id, choices };
        const permuted = permuteChoices(item);
        expect(permuted.choices.map((c) => c.id)).toEqual(choices.map((c) => c.id));
        expect(permuted.expected).not.toBe(item.expected_output);
        const originalText = choices.find((c) => c.id === item.expected_output)!.text;
        expect(permuted.choices.find((c) => c.id === permuted.expected)!.text).toBe(originalText);
      }
    }
  });

  it("renders the same default template as the Python engine", () => {
    expect(formatPrompt({ prompt: "Q?", choices: ABCD.slice(0, 2) })).toBe("Q?\n\nChoices:\na. 54\nb. 56\n\nAnswer with the choice label only.");
    expect(formatPrompt({ prompt: "Q?", choices: ABCD.slice(0, 1) }, "qa_block")).toContain("Options:\n(a) 54");
  });
});

describe("paired statistics and decisions", () => {
  it("is deterministic and supports a large, consistent drop", () => {
    const left = Array(20).fill(1);
    const right = Array(20).fill(0);
    const stats = pairedStats(left, right)!;
    expect(stats).toEqual(pairedStats(left, right));
    expect(stats.gap).toBe(1);
    expect(stats.permutation_p_value).toBeLessThan(0.001);
    expect(classify(stats, stats.permutation_p_value).direction).toBe("supports");
  });

  it("calls stable behavior evidence against, and small samples inconclusive", () => {
    const stable = pairedStats(Array(12).fill(1), Array(12).fill(1))!;
    expect(classify(stable, 1).direction).toBe("contradicts");
    const tiny = pairedStats([1, 1, 1], [0, 0, 0])!;
    expect(classify(tiny, 0.001).rule).toContain("fewer than 10");
    expect(pairedStats([], [])).toBeNull();
  });

  it("matches the Python Benjamini-Hochberg vector", () => {
    const adjusted = benjaminiHochberg([0.04, 0.001, 0.02]);
    expect(adjusted[0]).toBeCloseTo(0.04);
    expect(adjusted[1]).toBeCloseTo(0.003);
    expect(adjusted[2]).toBeCloseTo(0.03);
  });

  it("builds matrix rows with the strongest support and explicit gaps", () => {
    const rows = evidenceMatrix(
      [
        { detector_id: "x", status: "complete", direction: "supports", strength: "weak_indirect" },
        { detector_id: "y", status: "complete", direction: "contradicts", strength: "against" },
        { detector_id: "z", status: "not_run", direction: "inconclusive", strength: "unavailable" },
      ],
      [["h1", ["x", "y"]], ["h2", ["y"]], ["h3", ["z", "missing"]]],
    );
    expect(rows.map((row) => row.confidence)).toEqual(["weak_indirect", "against", "unavailable"]);
    expect(rows[2]!.unavailable).toEqual(["z", "missing"]);
  });

  it("recognizes reasoning models", () => {
    for (const id of ["o3-mini", "gpt-5", "openai/o4-mini", "deepseek-reasoner", "deepseek-r1", "gemini-2.5-flash", "qwq-32b"]) {
      expect(isReasoningModel(id)).toBe(true);
    }
    for (const id of ["gpt-4o-mini", "llama-3.3-70b-versatile", "claude-haiku-5-5", "mistral-small-latest"]) {
      expect(isReasoningModel(id)).toBe(false);
    }
  });
});

describe("parseAnswer is linear on adversarial model output (no ReDoS)", () => {
  it.each([
    ["answer" + " ".repeat(50_000) + "!"],
    ["answer is" + " \t\n".repeat(20_000) + "("],
    ["_".repeat(50_000) + "!"],
    ["**".repeat(25_000) + "!"],
    ["option ".repeat(10_000) + "!"],
    ["The final answer ".repeat(5_000)],
  ])("%#", (text) => {
    const started = performance.now();
    expect(parseAnswer(text, ABCD)).toBeNull();
    expect(performance.now() - started).toBeLessThan(500);
  });

  it("still reads multi-line statements", () => {
    expect(parseAnswer("Let me think.\n\nThe answer is\n\t(C)", ABCD)).toBe("c");
    expect(parseAnswer("Answer:\n**B**", ABCD)).toBe("b");
  });
});
