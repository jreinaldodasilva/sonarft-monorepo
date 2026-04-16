# SonarFT Web App Software Documentation (Version 1.0.0)

SonarFT: System Oscillator for Navigation and Ranging in Financial Trade

Version: 1.0.0.0

Initial Date: March 18, 2023

Last Update: August 27, 2023, 18:00

## Overview

SonarFT, an acronym for "System Oscillator for Navigation and Ranging in Financial Trade," draws inspiration from the SONAR technology used in navigation and underwater detection. It signifies a tool designed to monitor market oscillations and trends with the aim of identifying promising trading opportunities.

The term 'FT' stands for "Financial Trade," thereby emphasizing the application's purpose.

Consequently, SonarFT serves as a dynamic system for tracking and analyzing market oscillations and trends to discover profitable trading opportunities.

A system oscillator, in broad terms, refers to a device or component that generates a periodic or oscillating signal. In electronic and communication systems, oscillators are used to create waveforms such as sine waves, square waves, or other types of periodic signals. These signals serve various purposes, including synchronization, timing, frequency generation, and modulation.

Within the realm of finance or financial trading, a system oscillator might represent a tool or algorithm that generates a signal based on market data and trends. This signal aids in identifying market fluctuations, trends, or patterns that could be pivotal for trading decisions. Financial oscillators, capable of analyzing historical data or real-time market information, play a critical role in technical analysis and automated trading systems. Commonly employed financial oscillators include the Relative Strength Index (RSI), Moving Average Convergence Divergence (MACD), and Stochastic Oscillator.

SonarFT is a versatile trading bot, suitable for both multi-market, cross-exchange trading as well as single-exchange trading. It persistently tracks and analyzes market oscillations and trends to detect trading opportunities, consequently generating a trade packet for execution and profit generation.

## SonarFT Development Structure, Usage and Mechanisms

### Structure

SonarFT employs a modular architecture, diligently incorporating design patterns and clean coding principles. Utilizing the Python language and encapsulating the Object-Oriented Programming (OOP) paradigm, it manifests classes assigned with distinct responsibilities. For clarity and easy maintenance, each class is preserved in a separate file, thereby promoting a structure that is coherent, manageable, and easily modifiable.

The present structure of SonarFT incorporates 10 Python classes, each located within their dedicated Python files.

They include:

**Initiator Classes** : Initiation is the starting point of any operation. These classes are the genesis of a bot's lifecycle, tasked with initializing a bot instance, bootstrapping necessary parameters and configurations, and setting the stage for the execution of the selected strategy.

 **Strategy Classes** : Strategy forms the heart of any trading operation. In SonarFT, these classes play a central role by encapsulating specific trading strategies. They embody the decision-making logic that drives the bot's trading behavior.

 **Strategy Support Classes** : Support is the backbone of any effective system. These classes provide essential utility and calculation functions that aid in implementing the trading strategies. They supply necessary inputs and perform ancillary tasks to support the primary strategy operations.

 **API Management Classes** : Smooth interaction with external systems is crucial in trading. These classes manage all API communication aspects, including sending requests, handling responses, and managing data. They serve as the link between SonarFT and the outside world, particularly the trading platforms.

 **Mathematical Classes** : Precision is paramount in financial calculations. These classes house all the mathematical functions and algorithms used in market analysis, strategy formulation, and profit calculation. They maintain the precision and accuracy of the bot's operations.

 **General Helper Classes** : These classes are the multitaskers of SonarFT. They perform a variety of functions that assist in the overall functioning of the bot. From data formatting to logging activities, they fill in the gaps in the bot's operational framework.

### Usage

#### Launching the Bot

#### Configuring Parameters and Settings

Initial parameters and configurations are defined in these files: `config_parameters.json`, `config_exchanges.json`, `config_symbols.json`, `config_fees.json` and `config.json`.

To customize your configuration, either select an existing configuration from `config.json` or create your own within that file.

To create a new configuration, refer to each configuration file for available options. To add a new exchange, symbol, parameters, or fees, simply include them in their respective files. Subsequently, create the new configuration in `config.json`.

### Core Mechanisms

SonarFT Bot operates through a systematic process comprising several key steps, all designed to optimize trading performance. Below are the initial three steps, which lay the groundwork for the bot's trading operations:

1. **Setting Initial Trading Prices** : The first step involves the bot establishing the bid (buy) and ask (sell) prices for the trading asset. These prices form the basis of the bot's trading operations.
2. **Adjusting trading prices** : Once the bid and ask prices have been established, the bot then adjusts these prices to maximise potential profits. This adjustment also aims to keep the prices within a realistic range that allows effective execution of buy and sell orders on the trading platform.
3. **Validating the price difference and covering trading fees** : In the final preparatory step, the bot calculates the price differential between the adjusted bid and ask prices. This calculation aims to verify that the margin is sufficient to cover the trading fees associated with both buying and selling. This step is critical in preventing the execution of trades that would not yield a net profit once trading fees are accounted for.
