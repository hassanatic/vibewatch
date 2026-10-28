# vibewatch

Small vibration condition-monitoring toolkit for rotating machines: pumps, fans, motors, gearboxes,
conveyor drives.

It does three things:

1. **Waveform to features.** Takes raw acceleration samples from a sensor and computes broadband
   velocity RMS in mm/s over 10-1000 Hz (the band ISO 10816-3 uses), acceleration RMS and the dominant
   frequency. Velocity comes from integrating in the frequency domain, which also drops DC, gravity
   and slow drift that would wreck a time-domain integral.
2. **Severity zones.** Classifies a velocity RMS value into ISO 10816-3 zones A to D for the machine
   class (group 1 large machines or group 2 medium machines, rigid or flexible mounting).
3. **Per-asset trend.** Compares each machine with its own history: a median baseline from its first
   readings, the ratio of the latest reading to that baseline, a slope fitted over the last 14 days,
   and how many days until the next zone limit at that slope. A machine can be in a good zone and
   still be getting worse quickly, and that is usually the earlier warning.

## Status rules

| status | when |
|---|---|
| alarm | zone D |
| alert | zone C, or latest reading at least 2.5x its baseline |
| watch | at least 1.5x baseline, or the next zone limit is less than 30 days away at the current slope |
| ok | none of the above |

The slope uses only recent readings on purpose. A machine that ran flat for weeks and started
climbing last week would otherwise have that climb averaged away by its quiet history; there is a
test for exactly that case.

## Usage

```bash
pip install -e ".[test]"

# features and zone from one capture (one column of acceleration in m/s^2)
python -m vibewatch waveform capture.csv --fs 3200

# status per asset from feature readings (asset_id,timestamp,velocity_rms_mm_s)
python -m vibewatch report examples/readings.csv --group 2 --mounting rigid
```

```
alarm  gearbox-4            4.66 mm/s  zone D  zone D, 1.7x baseline
watch  pump-3               0.90 mm/s  zone A  2.2x baseline, next limit in 15 days
watch  crusher-fan-2        1.75 mm/s  zone B  next limit in 26 days
ok     conveyor-drive-1     1.11 mm/s  zone A  -
```

`report` exits with code 1 when any asset is in alarm, so it can sit in a scheduled job. `--json`
prints the full status per asset.

## Tests

```bash
pytest -q
```

The signal tests use tones whose velocity RMS has a closed form (a sine of amplitude A at f Hz in
acceleration has velocity RMS A / (2 pi f) / sqrt(2)), two-tone root-sum-square, an out-of-band tone,
and a gravity offset. The trend tests cover steady, rising, jumping and zone D machines.

## Limits

This is a learning project built on synthetic data. It has not been validated on real sensor
captures, it does not do envelope analysis, bearing fault frequencies or order tracking, and the
zone limits are the generic ISO 10816-3 values, not limits tuned for a specific machine.
