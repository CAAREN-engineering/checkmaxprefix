## Notes on data structures used

Ideally, the extracted configuration from the router would be a list of dictionaries with the following keys:
* ASN (this is guaranteed to be unique and used to query peeringDB)
* groupname (used to generate set commands)
* configured v4 prefixes
* configured v6 prefixes

The configuration coming from the router has v6 peers separately from v4 peers, which means we can't construct the
the dictionary at one time.  When a new peer is read, we would need to search the list to see if the ASN is present.

Is there a better way to handle this?