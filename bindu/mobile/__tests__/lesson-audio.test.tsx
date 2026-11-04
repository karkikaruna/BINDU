jest.mock("@/lib/storage", () => ({ safeStorage: { getItem: async () => null, setItem: async () => undefined, removeItem: async () => undefined } }));
jest.mock("@/lib/speech", () => ({ speakNepali: jest.fn(async () => "ok"), stopSpeech: jest.fn() }));
// Icon fonts and images are bundled assets that need a registry the test runner lacks; render plain stand-ins.
jest.mock("@expo/vector-icons", () => ({ Ionicons: () => null }));
jest.mock("@/assets/brand/speaker_icon.png", () => ({ uri: "speaker.png" }));
let mockLessonId = "1";
jest.mock("expo-router", () => ({ router: { back: jest.fn() }, useLocalSearchParams: () => ({ id: mockLessonId }) }));
jest.mock("react-native-safe-area-context", () => {
  const { View } = require("react-native");
  return { SafeAreaView: View, SafeAreaProvider: View };
});

/* eslint-disable @typescript-eslint/no-require-imports */
import { act, fireEvent, render, screen } from "@testing-library/react-native";
import { allLessons, findLesson } from "@/lib/curriculum";
import { speakNepali, stopSpeech } from "@/lib/speech";
import { useProgress } from "@/stores/progress";
const LessonPlayer = require("@/app/lesson/[id]").default as React.ComponentType;

const speakNe = speakNepali as jest.Mock;
const lesson = findLesson(1)!;
const first = lesson.exercises[0];

beforeEach(() => {
  mockLessonId = "1";
  jest.useFakeTimers();
  jest.clearAllMocks();
  useProgress.getState().reset();
});
afterEach(() => jest.useRealTimers());

describe("lesson player audio", () => {
  it("lesson 1 opens on a multiple-choice question", async () => {
    expect(first.type).toBe("multiple_choice");
  });

  it("reads the question aloud on its own when it appears, and again with the speaker icon", async () => {
    await render(<LessonPlayer />);
    expect(speakNe).not.toHaveBeenCalled(); // a short beat first
    await act(async () => { jest.advanceTimersByTime(400); });
    expect(speakNe).toHaveBeenCalledTimes(1);
    expect(speakNe).toHaveBeenCalledWith(first.prompt_ne);

    await act(async () => { await fireEvent.press(screen.getByTestId("play-question")); });
    expect(speakNe).toHaveBeenCalledTimes(2);
    expect(speakNe).toHaveBeenLastCalledWith(first.prompt_ne);
  });

  it("tapping an answer option says it aloud and selects it, with no speaker icon on the options", async () => {
    await render(<LessonPlayer />);
    for (const [i, option] of first.options.entries()) {
      expect(screen.queryByTestId(`hear-option-${i}`)).toBeNull();
      await act(async () => { await fireEvent.press(screen.getByTestId(`option-${i}`)); });
      expect(speakNe).toHaveBeenLastCalledWith(option);
    }
    expect(speakNe).toHaveBeenCalledTimes(first.options.length);
    expect(screen.getByTestId("check-btn").props.accessibilityState.disabled).toBe(false);
  });

  it("the learner picks and checks an answer; no speaker icon appears on the feedback bar", async () => {
    await render(<LessonPlayer />);
    const right = first.options.indexOf(first.answer[0]);
    await fireEvent.press(screen.getByTestId(`option-${right}`));
    await fireEvent.press(screen.getByTestId("check-btn"));
    expect(screen.getByText("Correct!")).toBeTruthy();
    expect(screen.queryByTestId("hear-answer")).toBeNull();
  });

  it("shows a message when Nepali audio can't be produced", async () => {
    speakNe.mockResolvedValueOnce("unavailable");
    await render(<LessonPlayer />);
    await act(async () => { await fireEvent.press(screen.getByTestId("option-0")); });
    expect(screen.getByText(/Nepali audio isn't available/)).toBeTruthy();
  });

  it("stops speaking when the lesson screen closes", async () => {
    const { unmount } = await render(<LessonPlayer />);
    await unmount();
    expect(stopSpeech).toHaveBeenCalled();
  });

  it("moving to the next question reads that question", async () => {
    await render(<LessonPlayer />);
    await act(async () => { jest.advanceTimersByTime(400); });
    const right = first.options.indexOf(first.answer[0]);
    await fireEvent.press(screen.getByTestId(`option-${right}`));
    await fireEvent.press(screen.getByTestId("check-btn"));
    await fireEvent.press(screen.getByTestId("continue-btn"));
    await act(async () => { jest.advanceTimersByTime(400); });
    expect(speakNe).toHaveBeenLastCalledWith(lesson.exercises[1].prompt_ne);
  });

  it("word-ordering: tapping a tile says that word, and there is no sentence speaker", async () => {
    const target = allLessons.find((l) => l.exercises.some((e) => e.type === "word_bank"))!;
    const at = target.exercises.findIndex((e) => e.type === "word_bank");
    mockLessonId = String(target.id);
    await render(<LessonPlayer />);
    const tapTile = async (word: string) => { await act(async () => { await fireEvent.press(screen.getAllByText(word)[0]); }); };
    // answer everything before the word-ordering exercise correctly
    for (const ex of target.exercises.slice(0, at)) {
      if (ex.type === "multiple_choice") await fireEvent.press(screen.getByTestId(`option-${ex.options.indexOf(ex.answer[0])}`));
      else for (const w of ex.answer) await tapTile(w);
      await fireEvent.press(screen.getByTestId("check-btn"));
      await fireEvent.press(screen.getByTestId("continue-btn"));
    }
    const ex = target.exercises[at];
    speakNe.mockClear();
    await tapTile(ex.answer[0]);
    expect(speakNe).toHaveBeenLastCalledWith(ex.answer[0]);
    await tapTile(ex.answer[1]);
    expect(screen.queryByTestId("hear-sentence")).toBeNull();
  });
});