# 핵심 주식 리스트 (S&P 100 + Nasdaq-100 중복 제거)
# 총 169개 자산

CORE_STOCK_ASSETS = [
    # === S&P 100 ===
    "AAPL",  # Apple Inc.
    "ABBV",  # AbbVie
    "ABT",   # Abbott Laboratories
    "ACN",   # Accenture
    "ADBE",  # Adobe Inc.
    "AIG",   # American International Group
    "AMD",   # Advanced Micro Devices
    "AMGN",  # Amgen
    "AMT",   # American Tower
    "AMZN",  # Amazon
    "AVGO",  # Broadcom
    "AXP",   # American Express
    "BA",    # Boeing
    "BAC",   # Bank of America
    "BK",    # BNY Mellon
    "BKNG",  # Booking Holdings
    "BLK",   # BlackRock
    "BMY",   # Bristol Myers Squibb
    "BRK.B", # Berkshire Hathaway (Class B)
    "C",     # Citigroup
    "CAT",   # Caterpillar Inc.
    "CL",    # Colgate-Palmolive
    "CMCSA", # Comcast
    "COF",   # Capital One
    "COP",   # ConocoPhillips
    "COST",  # Costco
    "CRM",   # Salesforce
    "CSCO",  # Cisco
    "CVS",   # CVS Health
    "CVX",   # Chevron Corporation
    "DE",    # Deere & Company
    "DHR",   # Danaher Corporation
    "DIS",   # Walt Disney Company (The)
    "DUK",   # Duke Energy
    "EMR",   # Emerson Electric
    "FDX",   # FedEx
    "GD",    # General Dynamics
    "GE",    # GE Aerospace
    "GILD",  # Gilead Sciences
    "GM",    # General Motors
    "GOOG",  # Alphabet Inc. (Class C)
    "GOOGL", # Alphabet Inc. (Class A)
    "GS",    # Goldman Sachs
    "HD",    # Home Depot
    "HON",   # Honeywell
    "IBM",   # IBM
    "INTC",  # Intel
    "INTU",  # Intuit
    "ISRG",  # Intuitive Surgical
    "JNJ",   # Johnson & Johnson
    "JPM",   # JPMorgan Chase
    "KO",    # Coca-Cola Company (The)
    "LIN",   # Linde plc
    "LLY",   # Eli Lilly and Company
    "LMT",   # Lockheed Martin
    "LOW",   # Lowe's
    "MA",    # Mastercard
    "MCD",   # McDonald's
    "MDLZ",  # Mondelēz International
    "MDT",   # Medtronic
    "MET",   # MetLife
    "META",  # Meta Platforms
    "MMM",   # 3M
    "MO",    # Altria
    "MRK",   # Merck & Co.
    "MS",    # Morgan Stanley
    "MSFT",  # Microsoft
    "NEE",   # NextEra Energy
    "NFLX",  # Netflix, Inc.
    "NKE",   # Nike, Inc.
    "NOW",   # ServiceNow
    "NVDA",  # Nvidia
    "ORCL",  # Oracle Corporation
    "PEP",   # PepsiCo
    "PFE",   # Pfizer
    "PG",    # Procter & Gamble
    "PLTR",  # Palantir Technologies
    "PM",    # Philip Morris International
    "PYPL",  # PayPal
    "QCOM",  # Qualcomm
    "RTX",   # RTX Corporation
    "SBUX",  # Starbucks
    "SCHW",  # Charles Schwab Corporation
    "SO",    # Southern Company
    "SPG",   # Simon Property Group
    "T",     # AT&T
    "TGT",   # Target Corporation
    "TMO",   # Thermo Fisher Scientific
    "TMUS",  # T-Mobile US
    "TSLA",  # Tesla, Inc.
    "TXN",   # Texas Instruments
    "UBER",  # Uber
    "UNH",   # UnitedHealth Group
    "UNP",   # Union Pacific Corporation
    "UPS",   # United Parcel Service
    "USB",   # U.S. Bancorp
    "V",     # Visa Inc.
    "VZ",    # Verizon
    "WFC",   # Wells Fargo
    "WMT",   # Walmart
    "XOM",   # ExxonMobil

    # === Nasdaq-100 (S&P 100과 중복 제외 68개) ===
    "ABNB",  # Airbnb
    "AEP",   # American Electric Power
    "APP",   # AppLovin
    "ARM",   # Arm Holdings
    "ASML",  # ASML Holding
    "AZN",   # AstraZeneca
    "TEAM",  # Atlassian
    "ADSK",  # Autodesk
    "ADP",   # Automatic Data Processing
    "AXON",  # Axon Enterprise
    "BKR",   # Baker Hughes
    "BIIB",  # Biogen
    "CDNS",  # Cadence Design Systems
    "CDW",   # CDW Corporation
    "CHTR",  # Charter Communications
    "CTAS",  # Cintas
    "CCEP",  # Coca-Cola Europacific Partners
    "CTSH",  # Cognizant
    "CEG",   # Constellation Energy
    "CPRT",  # Copart
    "CSGP",  # CoStar Group
    "CRWD",  # CrowdStrike
    "CSX",   # CSX Corporation
    "DDOG",  # Datadog
    "DXCM",  # DexCom
    "FANG",  # Diamondback Energy
    "DASH",  # DoorDash
    "EA",    # Electronic Arts
    "EXC",   # Exelon
    "FAST",  # Fastenal
    "FTNT",  # Fortinet
    "GEHC",  # GE HealthCare
    "GFS",   # GlobalFoundries
    "IDXX",  # Idexx Laboratories
    "KDP",   # Keurig Dr Pepper
    "KLAC",  # KLA Corporation
    "KHC",   # Kraft Heinz
    "LRCX",  # Lam Research
    "LULU",  # Lululemon
    "MAR",   # Marriott International
    "MRVL",  # Marvell Technology
    "MELI",  # Mercado Libre
    "MCHP",  # Microchip Technology
    "MU",    # Micron Technology
    "MSTR",  # MicroStrategy
    "MNST",  # Monster Beverage
    "NXPI",  # NXP Semiconductors
    "ORLY",  # O'Reilly Automotive
    "ODFL",  # Old Dominion Freight Line
    "ON",    # Onsemi
    "PCAR",  # Paccar
    "PANW",  # Palo Alto Networks
    "PAYX",  # Paychex
    "PDD",   # PDD Holdings
    "REGN",  # Regeneron Pharmaceuticals
    "ROPR",  # Roper Technologies
    "ROST",  # Ross Stores
    "SHOP",  # Shopify
    "SOLS",  # Solstice Advanced Materials
    "SNPS",  # Synopsys
    "TTWO",  # Take-Two Interactive
    "TRI",   # Thomson Reuters
    "TTD",   # Trade Desk (The)
    "VRSK",  # Verisk Analytics
    "VRTX",  # Vertex Pharmaceuticals
    "WBD",   # Warner Bros. Discovery
    "WDAY",  # Workday, Inc.
    "XEL",   # Xcel Energy
    "ZS"     # Zscaler
]

