# Try it: the intensity-duration plane

How much rain does it take? Pick a region, a duration and the rain that fell,
and see where it stands against the Italian threshold and against the
landslides of the past. Everything runs in your browser: no data leave it.

!!! warning "A threshold exceeded is not an alert"
    It says the rain is like the rain that triggered landslides before. The
    official alert in Italy is the
    [criticality bulletin](https://rischi.protezionecivile.gov.it/it/meteo-idro/allertamento/)
    of the Dipartimento della Protezione Civile.

<div class="rt-explainer" markdown="0">
  <div class="rt-controls">
    <label><span>Region</span>
      <select id="rt-region"></select>
    </label>
    <label><span>Duration: <output id="rt-d-out">24</output> h</span>
      <input id="rt-d" type="range" min="0" max="2.2253" step="0.0001" value="1.3802">
    </label>
    <label><span>Rain: <output id="rt-e-out">50</output> mm</span>
      <input id="rt-e" type="range" min="0" max="2.6021" step="0.0001" value="1.699">
    </label>
  </div>
  <svg id="rt-plane" viewBox="0 0 640 420" role="img" aria-label="Duration against mean intensity, log-log: past landslides of the macroregion as grey dots, the T5 threshold as a line, your rain as a star"></svg>
  <div id="rt-answer" aria-live="polite"></div>
</div>

**How to read it.** Each grey dot is a landslide of the macroregion, placed by
the duration and mean intensity of the rain that triggered it (e-ITALICA,
measured at rain gauges). The blue line is the T5 threshold: 5 % of those
landslides sit under it. The star is your rain. Its distance from the line is
the exceedance, in decades: +0.3 is twice the threshold intensity, +1 ten
times.

**What it does not say.** Whether a landslide will happen, or where: slope,
soil and the wetness of the weeks before matter as much as the rain. How often
the threshold is passed when nothing happens: that is the
[cost in false alarms](api/measure.md), and it is not in a landslide catalogue.

The thresholds and the landslides come from the library and from e-ITALICA v4
(Brunetti et al. 2024, [doi:10.5281/zenodo.14204473](https://doi.org/10.5281/zenodo.14204473),
CC BY 4.0), written by `docs/make_explainer_data.py`.
