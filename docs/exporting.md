---
---

## Exporting your data from Untappd

**Reminder: You have to be an Untappd Supporter to use this feature.**

You can export two kinds of data from Untappd - Checkins (aka Beer History) and Lists. 

<img src="images/untappd-menu.png" width="300" alt="Untappd Profile menu, with Beer History and Lists highlighted">

⚠️ For some reason, the export buttons are not shown when you view Untappd on a small mobile device - you'll have to do 
this on a tablet, laptop or desktop.

### Exporting Checkins

Your "Beer History" page gives you the following options:

<img src="images/untappd-history-json.png" width="600" alt="Part of Untappd Checkins page, with JSON export highlighted">

Beerbot works with JSON data, but you can also request a CSV export for your own use.

To export your checkin history, click the JSON button, wait a couple of minutes (usually), then check your email 
for a message entitled "Your Export from Untappd".

#### Tracking Consumption

As Untappd is primarily geared toward sharing and enjoying beer, it doesn't track the measure of each drink. 
However, one of Beerbot's uses is to help you gauge and manage consumption, so it needs that data.

It can obtain it in one of two ways. If you've saved the "Serving Style" field in your checkin, it'll make a guess from 
that. It assumes that Draft and Bottle are half-pints, Cans and Bottles are 300ml, and Tasters are 150ml. 
It can't guess at anything else so will skip that beer when calculating consumption.
If you download and run the code yourself, you can edit these defaults, but they're fixed for email users.

If these defaults don't work for you, you want to note that you checked in a taste or sip, or you just want to be more 
precise, you can embed the measure in your comment field, in `[square brackets]`. 

Brewbot recognises a number of measures, eg:

    [pint] or [liter]
    [half], [third] or [quarter]
    [2/3], [1/2], [1/3] etc
    [330ml]
    [50cl]
    [2pints]
    [halfliter]

Any fractional units, whether word or numeric, are assumed to be fractions of a pint if liter(s) are not specified.

<img src="images/untappd-mobile-checkin-measures.png" width="300" alt="Untappd app checkin screen">

### Exporting a List

Individual list pages also allow you to export their data. As before, Beerbot expects JSON data.

<img src="images/untappd-list-json.png" width="600" alt="Part of Untappd List page, with JSON export highlighted">

To export a list, click the JSON button, wait a couple of minutes (usually), then check your email 
for a message entitled "Your Export from Untappd".

Beerbot works best with lists that have "Additional Item Details", as its list processing functionality is geared
towards managing a home collection. You can manage this in the app when you edit the list:

<img src="images/untappd-mobile-list-details.png" width="300" alt="Untappd app list details screen, with 'Addtional Item Details' highlighted">

The more information you add to each item on your list, the more Beerbot can do with it. In particular, adding 
Quantity, Serving Style and Best By Date is recommended.

## Further Information

Untappd's documentation on list exports is 
[here](https://help.untappd.com/support/solutions/articles/25000001978-where-can-i-find-the-exportable-data-feature-).


{% include footer.md %}