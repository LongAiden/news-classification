1. Import get_analyzer and class NewsAnalyzer from news_analyzer.py
- Note GEMINI API KEY: GEMINI_KEY = os.getenv('GOOGLE_API_KEY')

2.How to run:
analyzer = get_analyzer()

title = "Few CRE companies have achieved their AI goals. Here's why"
text_content = '''Few CRE companies have achieved their AI goals. Here\'s why Skip Navigation Markets Pre-Markets U.S. Markets Europe Markets China Markets Asia Markets World Markets Currencies Cryptocurrency Futures & Commodities Bonds Funds & ETFs Business Economy Finance Health & Science Media Real Estate...'''

3. Get the output
test = await analyzer.analyze_with_contents(text=text_content, title=title)

output = test.model_dump()

=> Output should be like this
{'page_title': "Few CRE companies have achieved their AI goals. Here's why",
 'is_financial': 'Yes',
 'country': [],
 'sector': [],
 'companies': [],
 'confident_score': 9.5,
 'sentiment': 'Neutral',
 'summary_en': 'A recent JLL survey indicates that while commercial real estate (CRE) companies are increasingly adopting AI, with 88% piloting it for an average of five use cases, only 5% have fully achieved their AI goals. This is attributed to the moving goalposts, as companies now aim to tie AI to revenue and business growth rather than just operational efficiencies, requiring fundamental changes to operating models.',
 'summary_tr': 'Yeni bir JLL anketine göre, ticari gayrimenkul (TG) şirketleri giderek daha fazla YZ benimsemesine rağmen (ortalamada beş kullanım durumu için pilot uygulama yapanların %88',
 'extracted_characters': 7365}