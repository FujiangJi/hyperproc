"""Generate tests/data/r_reference/prisma_smoothing.npz by running R itself.

``test_smoothing_r.py`` claims the Python port of the PRISMA smoothing pipeline
reproduces the original R to about 1e-8. That claim is only worth anything if
R's own answers are checked in, so this script produces them.

Run it only when the reference needs rebuilding, and read the diff:

    python tests/tools/make_r_reference.py

Needs R with ``pracma`` and ``FieldSpectroscopyCC``:

    install.packages("pracma")
    remotes::install_github("tommasojulitta/FieldSpectroscopyCC")

The 40 spectra are drawn deterministically from the PRISMA L2D granule in
tests/data, so re-running gives the same file unless the granule changes.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import warnings
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tests" / "data"
OUT = DATA / "r_reference" / "prisma_smoothing.npz"
RLIB = Path.home() / "R" / "x86_64-pc-linux-gnu-library" / "4.5"

# Where the spectra come from: a fixed block of the granule, strided to 40.
WINDOW = dict(y=slice(500, 520), x=slice(500, 520))
N_SPECTRA = 40
DF = 60.0
THRESHOLD = 0.018
FIXED_LAMBDA = 1e-8

R_SCRIPT = r"""
lib <- Sys.getenv("R_REF_LIB")
if (nzchar(lib)) .libPaths(c(lib, .libPaths()))
suppressMessages(library(pracma))

args <- commandArgs(trailingOnly = TRUE)
indir <- args[1]

wl      <- as.numeric(readLines(file.path(indir, "wl.txt")))
spectra <- as.matrix(read.csv(file.path(indir, "spectra.csv"), header = FALSE))
excl    <- read.csv(file.path(indir, "exclude.csv"), header = FALSE)   # before the fit
maskaft <- read.csv(file.path(indir, "mask_after.csv"), header = FALSE) # after the fit

in_ranges <- function(w, r) {
  out <- rep(FALSE, length(w))
  for (i in seq_len(nrow(r))) out <- out | (w >= r[i, 1] & w <= r[i, 2])
  out
}
drop_before <- in_ranges(wl, excl)
drop_after  <- in_ranges(wl, maskaft)

n <- nrow(spectra); nb <- length(wl)
spikes   <- matrix(FALSE, n, nb)
smoothed <- matrix(NA_real_, n, nb)
params   <- matrix(NA_real_, n, 4)
colnames(params) <- c("ratio", "spar", "lambda", "df")

for (i in seq_len(n)) {
  s <- as.numeric(spectra[i, ])

  # step 1 - pracma::findpeaks, blanking peak / start / end of every peak
  pk <- findpeaks(s, threshold = 0.018)
  m <- rep(FALSE, nb)
  if (!is.null(pk)) {
    idx <- as.vector(pk[, 2:4])
    idx <- idx[!is.na(idx) & idx >= 1 & idx <= nb]
    m[idx] <- TRUE
  }
  spikes[i, ] <- m

  # step 2 - blank the instrument-artefact windows
  y <- s; y[m] <- NA; y[drop_before] <- NA

  # step 3 - smooth.spline through what survives, evaluated everywhere
  d <- data.frame(wl = wl, y = y)
  t <- na.omit(d)
  f <- smooth.spline(t$wl, t$y, df = 60)
  params[i, ] <- c(f$ratio, f$spar, f$lambda, f$df)
  sm <- predict(f, wl)$y

  # step 4 - blank the deep water absorptions
  sm[drop_after] <- NA
  smoothed[i, ] <- sm
}

# the search removed: only the basis and penalty under test, on spectrum 1
s <- as.numeric(spectra[1, ]); m <- spikes[1, ]
y <- s; y[m] <- NA; y[drop_before] <- NA
t <- na.omit(data.frame(wl = wl, y = y))
f0 <- smooth.spline(t$wl, t$y, lambda = 1e-8)
fixed <- predict(f0, wl)$y
cat(sprintf("fixed-lambda df = %.10f\n", f0$df))

# %.17g is full double precision: write.table's default 15 significant digits
# is not enough for the 1e-12 comparisons, and na = "NaN" keeps numpy happy.
g17 <- function(m) {
  m <- as.matrix(m)
  out <- matrix(sprintf("%.17g", m), nrow = nrow(m))
  out[is.na(m)] <- "NaN"
  out
}
write.table(spikes,      file.path(indir, "r_spikes.csv"),   sep = ",", row.names = FALSE, col.names = FALSE)
write.table(g17(smoothed), file.path(indir, "r_smoothed.csv"), sep = ",", row.names = FALSE, col.names = FALSE, quote = FALSE)
write.table(g17(params),   file.path(indir, "r_params.csv"),   sep = ",", row.names = FALSE, col.names = FALSE, quote = FALSE)
write.table(g17(fixed),    file.path(indir, "r_fixed.csv"),    sep = ",", row.names = FALSE, col.names = FALSE, quote = FALSE)
cat("R side done\n")
"""


def main() -> int:
    import hyperproc as hp
    from hyperproc.spectral.smoothing import PRISMA_ARTEFACT_RANGES, PRISMA_MASK_AFTER

    hits = sorted(DATA.glob("PRISMA/PRS_L2D_STD_*.he5"))
    if not hits:
        print("no PRISMA L2D granule in tests/data; cannot build the reference")
        return 1
    ds = hp.open(hits[0])
    var = hp.main_var(ds)
    block = ds[var].isel(y=WINDOW["y"], x=WINDOW["x"]).values
    wl = np.asarray(ds.wavelength.values, dtype="float64")

    flat = block.reshape(-1, wl.size)
    finite = np.isfinite(flat).all(axis=1)
    flat = flat[finite]
    if flat.shape[0] < N_SPECTRA:
        print(f"only {flat.shape[0]} fully finite spectra in the block; need {N_SPECTRA}")
        return 1
    step = flat.shape[0] // N_SPECTRA
    spectra = np.ascontiguousarray(flat[::step][:N_SPECTRA], dtype="float64")
    print(f"{spectra.shape[0]} spectra x {wl.size} bands from {hits[0].name}")

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "wl.txt").write_text("\n".join(f"{v:.10f}" for v in wl))
        np.savetxt(d / "spectra.csv", spectra, delimiter=",", fmt="%.12g")
        np.savetxt(d / "exclude.csv", np.array(PRISMA_ARTEFACT_RANGES, dtype=float),
                   delimiter=",", fmt="%.6f")
        np.savetxt(d / "mask_after.csv", np.array(PRISMA_MASK_AFTER, dtype=float),
                   delimiter=",", fmt="%.6f")
        (d / "run.R").write_text(R_SCRIPT)

        env = {"R_REF_LIB": str(RLIB) if RLIB.is_dir() else ""}
        import os
        proc = subprocess.run(["Rscript", str(d / "run.R"), str(d)],
                              capture_output=True, text=True, env={**os.environ, **env})
        print(proc.stdout.strip() or proc.stderr.strip()[-800:])
        if proc.returncode != 0:
            print("R failed"); return 1

        r_spikes = np.loadtxt(d / "r_spikes.csv", delimiter=",", dtype=str)
        r_spikes = (np.char.upper(r_spikes) == "TRUE")
        r_smoothed = np.loadtxt(d / "r_smoothed.csv", delimiter=",")
        r_params = np.loadtxt(d / "r_params.csv", delimiter=",")
        r_fixed = np.loadtxt(d / "r_fixed.csv")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        OUT,
        wl=wl, spectra=spectra,
        r_spikes=r_spikes,
        r_ratio=r_params[:, 0], r_spar=r_params[:, 1],
        r_lambda=r_params[:, 2], r_df=r_params[:, 3],
        r_fixed_lambda=r_fixed,
        r_smoothed=r_smoothed,
    )
    print(f"wrote {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")
    print(f"  spikes flagged: {int(r_spikes.sum())} bands over {r_spikes.shape[0]} spectra")
    return 0


if __name__ == "__main__":
    sys.exit(main())
