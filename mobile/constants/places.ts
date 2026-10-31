// Small curated set (README 4.4 "Local Knowledge"). Descriptions are intentionally general and non-numeric;
// no opening hours, prices or ratings are stated because none are verified here.
export type CuratedPlace = { id: string; name: string; area: string; category: string; blurb: string };
export const CURATED_PLACES: CuratedPlace[] = [
  { id: "patan", name: "Patan Durbar Square", area: "Lalitpur", category: "Heritage site", blurb: "Newar palace complex with temples, courtyards and richly carved woodwork." },
  { id: "boudha", name: "Boudhanath Stupa", area: "Kathmandu", category: "Temples & monasteries", blurb: "A major Tibetan Buddhist stupa surrounded by monasteries and prayer-flag lanes." },
  { id: "swayambhu", name: "Swayambhunath", area: "Kathmandu", category: "Temples & monasteries", blurb: "Hilltop stupa complex overlooking the Kathmandu Valley." },
  { id: "bhaktapur", name: "Bhaktapur Durbar Square", area: "Bhaktapur", category: "Heritage site", blurb: "Medieval Newar city square; the town is known for juju dhau, a creamy curd." },
  { id: "pashupati", name: "Pashupatinath", area: "Kathmandu", category: "Temples & monasteries", blurb: "Hindu temple complex on the Bagmati River. Observe respectfully; some areas restrict entry." },
];
