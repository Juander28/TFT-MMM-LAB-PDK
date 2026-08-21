# Measurements

This directory is the drop point for the raw measurement data the models were
extracted from - the `.xls` sweeps out of the probe station:

```
measurements/
├── TFT1/{VDS,VGS,CAP,COX,TLM,HALL}/*.xls
├── TFT2/...
├── TFT3/...
└── test/*.xls
```

**The data itself is not tracked in git.** It is laboratory data, it is large,
and it belongs with the lab records rather than inside a PDK. Everything in
this repository that depends on it - the model cards, Cox, the contact
resistance, the drawn-to-printed bias - is already reduced to numbers, and
`docs/extraction/` holds the scripts that produced them, so the path from raw
sweep to model card stays auditable.

Copy the data in here if you want to re-run an extraction:

```bash
python3 docs/extraction/extract_params.py     # re-extracts Vto, Kp, lambda
python3 docs/extraction/validate_model.py     # simulated vs measured, 18 devices
python3 docs/extraction/contact_extract.py    # 2*Rc*W from R_on against L
```

`.gitignore` keeps this README and ignores everything else here.
