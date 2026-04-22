import React, { useState, useEffect } from "react";
import "./cryptoticker.css";

const COINGECKO_POLL_MS = 180_000;

type CoinEntry = [string, { usd: number }];

const CryptoTicker: React.FC = () => {
    const [cryptoData, setCryptoData] = useState<CoinEntry[]>([]);

    useEffect(() => {
        const fetchData = async (): Promise<void> => {
            try {
                const marketsRes = await fetch(
                    "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=20&page=1"
                );
                if (!marketsRes.ok) return;
                const markets = await marketsRes.json() as { id: string }[];
                const coinIds = markets.map((c) => c.id).join(",");

                const priceRes = await fetch(
                    `https://api.coingecko.com/api/v3/simple/price?ids=${coinIds}&vs_currencies=usd`
                );
                if (!priceRes.ok) return;
                const prices = await priceRes.json() as Record<string, { usd: number }>;
                setCryptoData(Object.entries(prices) as CoinEntry[]);
            } catch { /* CoinGecko fetch failed — ticker remains empty until next poll */ }
        };

        fetchData();
        const intervalId = setInterval(fetchData, COINGECKO_POLL_MS);
        return () => clearInterval(intervalId);
    }, []);

    return (
        <section className="crypto-banner-container">
            <div className="crypto-banner">
                <div className="inner">
                    {cryptoData.map((data, index) => (
                        <div key={index} className="crypto-item">
                            <span>{data[0].toUpperCase()}:</span>
                            <span>{` $${data[1].usd}`}</span>
                        </div>
                    ))}
                    {cryptoData.map((data, index) => (
                        <div key={`${index}-clone`} className="crypto-item">
                            <span>{data[0].toUpperCase()}:</span>
                            <span>{` $${data[1].usd}`}</span>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
};

export default CryptoTicker;
