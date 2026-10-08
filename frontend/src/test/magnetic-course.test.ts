import {describe,expect,it} from "vitest";
import {MAGNETIC_CITATIONS} from "../data/magnetic-course-citations";
import {magneticDerivations} from "../data/magnetic-course-derivations";
import {magneticLessons} from "../data/magnetic-survey-course";

describe("complete source-bound magnetic research course, not fit acceptance",()=>{
  it("has nine distinct canonical chapters and the same complete derivation inventory",()=>{
    expect(magneticLessons.map(l=>l.id)).toEqual(["original","physics","likelihood","prior","sparse","partition","native","diagnostics","custody"]);
    expect(Object.keys(magneticDerivations)).toEqual(magneticLessons.map(l=>l.id));
    expect(new Set(MAGNETIC_CITATIONS.map(c=>c.id)).size).toBe(4);
  });
  it.each(magneticLessons)("preserves bilingual derivation, equations, worked question and primary references for $id",lesson=>{
    const derivation=magneticDerivations[lesson.id];
    for(const text of [lesson.body,lesson.symbols,lesson.limit,...derivation.paragraphs,derivation.symbols,derivation.exercise,derivation.answer,derivation.implementation,...derivation.steps]){
      expect(text).toHaveLength(2);expect(text[0].length).toBeGreaterThan(10);expect(text[1].length).toBeGreaterThan(10);
    }
    expect(derivation.paragraphs).toHaveLength(2);expect(derivation.steps).toHaveLength(3);
    expect(lesson.equation.length).toBeGreaterThan(20);expect(derivation.equation.length).toBeGreaterThan(20);
    expect(lesson.references.length).toBeGreaterThan(0);
    for(const source of lesson.references){
      const citation=MAGNETIC_CITATIONS.find(c=>c.id===source.id);
      expect(citation?.url).toBe(source.url);expect(source.url).toMatch(/^https:\/\/raw\.githubusercontent\.com\//);
    }
  });
});
