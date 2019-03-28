## Notes on data structures used

Ideally, the extracted configuration from the router would be a list of dictionaries with the following keys:
* ASN (this is guaranteed to be unique and used to query peeringDB)
* groupname (used to generate set commands)
* configured v4 prefixes
* configured v6 prefixes

The configuration coming from the router has v6 peers separately from v4 peers, which means we can't construct the
the dictionary at one time.  When a new peer is read, we would need to search the list to see if the ASN is present.

Is there a better way to handle this?

<br />
<br />

In function `generateSetCommands`
there are a lot of nested, seemingly redundant 'if' statements:

                if 'family' in group:
                    if 'inet' in group['family'][0]:

this tests to see if family options are configured for this group (first test), and if so, which family (second test).

We can't test directly for inet vs inet6, because doing so would result in a key error- if there are no family options configured, then that dictionary key wont exist.

Maybe this could be replaced with a try/except block, but I"m not sure that's any better (faster) or cleaner
