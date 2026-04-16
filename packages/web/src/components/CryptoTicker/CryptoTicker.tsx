import React, { useState, useEffect } from "react";
import axios from "axios";
import "./cryptoticker.css";

type CoinEntry = [string, { usd: number }];

const CryptoTicker: React.FC = () => {
    const [cryptoData, setCryptoData] = useState<CoinEntry[]>([]);

    useEffect(() => {
        const fetchData = async (): Promise<void> => {
            try {
                const topCoinsResponse = await axios.get<{ id: string }[]>(
                    "https://api.coingecko.com/api/v3/coins/markets",
                    { params: { vs_currency: "usd", order: "market_cap_desc", per_page: 20, page: 1 } }
                );
                const coinIds = topCoinsResponse.data.map((coin) => coin.id).join(",");
                const response = await axios.get<Record<string, { usd: number }>>(
                    `https://api.coingecko.com/api/v3/simple/price?ids=${coinIds}&vs_currencies=usd`
                );
                setCryptoData(Object.entries(response.data) as CoinEntry[]);
            } catch { /* CoinGecko fetch failed — ticker remains empty until next poll */ }
        };

        fetchData();
        const intervalId = setInterval(fetchData, 180000);
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
