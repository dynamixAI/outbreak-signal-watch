# Outbreak Signal Watch

A data pipeline and live dashboard that tracks 10 lower-profile UK illnesses and 
flags statistically unusual rises as potential early outbreak signals.

## Why this exists

Outbreaks like the 2026 UK Salmonella outbreak often build up quietly for months 
before being formally detected — in that case, cases stretched back almost a year 
before genomic clustering revealed they were connected. This project asks: can 
routine surveillance data flag an unusual rise *before* it's officially recognised?

## What it does

- Pulls weekly/monthly case data from the UKHSA data dashboard API for 10 
  lower-profile diseases (not the ones dominating headlines like COVID or flu)
- Calculates a rolling baseline (average + standard deviation) for each disease
- Flags data points that rise significantly above the expected range
- Displays trends live as line charts, so a real rise is visible as it happens

## Diseases tracked

Invasive Group A Strep (iGAS), Scarlet fever, E. coli bacteraemia, C. difficile, 
Klebsiella spp., MRSA, MSSA, P. aeruginosa, Mpox (clade IIb), Parainfluenza

## Tech stack

- **Backend:** Python, Flask
- **Frontend:** HTML, Chart.js
- **Data source:** UKHSA data dashboard API
