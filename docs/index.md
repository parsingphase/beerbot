---
---
# Beerbot: doing more with your Untappd data

Beerbot is a tool to make better use of your [Untappd](https://untappd.com/) lists and checkin history. 
It generates convenient stock lists, weekly and monthly summaries of the beers you've drunk, 
and analysis of your favourite styles and venues. Outputs are CSVs that you can format, analyse and print in any 
spreadsheet program.

### Stock list
[<img src="images/bb-stocklist.png" alt="Example stocklist">](images/bb-stocklist.png) [Sample csv](files/stocklist-sample.csv)

### Weekly summary
[<img src="images/bb-checkin-summary.png" alt="Example weekly summary">](images/bb-checkin-summary.png) [Sample csv](files/checkin-summary-sample.csv)

### Breweries analysis
[<img src="images/bb-checkin-breweries.png" alt="Example summary">](images/bb-checkin-breweries.png) [Sample csv](files/checkin-breweries-sample.csv)

## Using Beerbot

To use it, you'll need to be able to use Untappd's export tools, which means you'll need a paid 
[Untappd Supporter Account](https://untappd.com/supporter).

You can use the tools in one of two ways - either download the code and run it yourself, or just forward your 
Untappd export emails to the service.

### Run at home
You'll need a little patience or some experience running Python code to do this. Everything is available and documented
at [{{ site.github.project_title }}]({{ site.github.repository_url }}#readme).

This is the slightly more powerful, but less convenient option.

### Forward by email
For maximum convenience you can just forward the export emails from Untappd to a robot address. 
At the moment, I'm not making this address globally available so that I can keep usage under control, 
so please email me at [richard@phase.org](mailto:richard@phase.org?subject=Beerbot Access Request) if you want to use 
this (doesn't matter if you don't know me, this is only about controlling numbers).

### Getting your data

The process for getting your data, whether for personal download or for email forwarding is described in 
"[Exporting your data](exporting.md)". 

### Making the best of Beerbot

Beerbot will make a best effort to process any export it's fed, but you can get a lot more out of it if you
[feed it the best data](feedingBeerbot.md).


{% include footer.md %}