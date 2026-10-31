export type Exercise = {
  id: number;
  type: "multiple_choice" | "word_bank";
  prompt: string;
  options: string[];
  tokens: string[];
  answer: string[];
  audio_url: string | null;
  order_index: number;
};
export type Lesson = { id: number; name: string; order_index: number; exercises: Exercise[] };
export type Unit = { id: number; name: string; order_index: number; color_theme: string | null; lessons: Lesson[] };
export type LessonsPayload = { units: Unit[] };
