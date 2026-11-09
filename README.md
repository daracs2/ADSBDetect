# ADSBDetect

Detecting GNSS interference (jamming) from ADS-B trace data using
position-quality indicators (NACp, NIC) reported by aircraft.

Raw data is not included in this repo. It is expected in
`$DATA_DIR/<YYYY.MM.DD>/traces/`.


The data is extracted ignoring the first ADSB version due to improportional noise, furthermore NACp values reading 0 are dropped as well, because they represent faulty GNSS transceivers rather than potential interference.
