export type BookLevel = {
  price: number;
  quantity: number;
};

export type OrderBookSnapshot = {
  bids: BookLevel[];
  asks: BookLevel[];
};

export type DetectorScore = {
  name: string;
  confidence: number;
  alert: boolean;
};
