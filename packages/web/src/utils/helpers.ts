import { getOrders, getTrades, TradeRecord } from "./api";

export const fetchAllOrders = async (botIds: string[]): Promise<TradeRecord[]> => {
    const results = await Promise.all(botIds.map((id) => getOrders(id)));
    return results.filter((r): r is TradeRecord[] => r !== null).flat();
};

export const fetchAllTrades = async (botIds: string[]): Promise<TradeRecord[]> => {
    const results = await Promise.all(botIds.map((id) => getTrades(id)));
    return results.filter((r): r is TradeRecord[] => r !== null).flat();
};
