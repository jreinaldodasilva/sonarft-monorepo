import { getOrders, getTrades, TradeRecord } from "./api";

export const fetchAllOrders = async (
    botIds: string[],
    clientId: string
): Promise<TradeRecord[]> => {
    const results = await Promise.all(botIds.map((id) => getOrders(id, clientId)));
    return results.filter((r): r is TradeRecord[] => r !== null).flat();
};

export const fetchAllTrades = async (
    botIds: string[],
    clientId: string
): Promise<TradeRecord[]> => {
    const results = await Promise.all(botIds.map((id) => getTrades(id, clientId)));
    return results.filter((r): r is TradeRecord[] => r !== null).flat();
};
