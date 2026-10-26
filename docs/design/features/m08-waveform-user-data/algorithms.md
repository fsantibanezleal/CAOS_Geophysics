# Proposed M08 calculation: literal algorithms and physical meaning

Status: PROPOSED, NOT_RUN. These equations specify the actual operations to implement after approval, not an executed field recipe. Inputs/bounds/errors are in [contracts](contracts.md). All arithmetic except raw integer counts/time identities is float64; complex operators are complex128. No interpolation, rotation, response fitting, posterior inference or model training occurs.

## 1. Observation and channel frame

For channel c, the integer samples d_c[n] are counts at exact source times t_c[n]=t0_c+n/fs. On the declared linear, time-invariant response epoch, their interpretation is

$$d_c[n] \simeq (h_c*q_c)(t_c[n])+b_c(t_c[n])+\eta_c[n],\qquad q_c=\mathbf a_c^\mathsf T\mathbf u.$$

Here q_c is the native projected displacement, velocity or acceleration, h_c includes all sensor/acquisition stages in counts per native SI unit, b_c is offset/trend and eta_c is unmodelled noise. The approximation does not make noise or calibration errors known. For azimuth alpha clockwise from true north and dip delta positive down, the projection on E,N,up is

$$\mathbf a_c=(\cos\delta\sin\alpha,\cos\delta\cos\alpha,-\sin\delta).$$

Angles are converted once from degrees to radians; source values/signs are retained. A dip -90 degrees points up. No ENZ array is manufactured from channel suffixes; no station energy combines differing quantities. Orientation/response semantics follow the [StationXML reference](https://docs.fdsn.org/projects/stationxml/en/latest/reference.html). We keep projection vectors, not an unverified inverse rotation.

## 2. Counts QC and conditioning

Raw samples are chronological admitted integer records, not an engine-merged zero-filled stream. Compute min/max, exact plateau runs, mean/RMS using safe float64 scaling, actual record gap/overlap intervals, flag counts and ADC-rail comparisons before physical processing. A bad clock/clip/continuity/epoch channel makes this first station-level lane QC-only; no quiet substitution of another channel. Empty/flat channels are retained failures. Unknown rail/timing accuracy is a warning under the explicit contract, not proof of quality.

Physical QC uses the explicit conditioning slice. Outside-only clipping/flags remain separate diagnostics; whole-record malformed data, identity/rate/continuity defects still block the lane. Compute extreme plateaus on the conditioning slice, not an unrelated outside value. A single selected measured channel needs no invented ENZ companions.

For each admitted channel, detrend the entire conditioning interval, not only the display/analysis subwindow. Let tau_n=(n-(N-1)/2)/fs. Compute

$$\bar d=N^{-1}\sum_n d_n,\quad b=\frac{\sum_n\tau_n(d_n-\bar d)}{\sum_n\tau_n^2},\quad x_n=d_n-\bar d-b\tau_n.$$

Store bar d (counts), b (counts/s), the fit interval and algorithm identity. A private copy goes through SciPy linear detrending; an independently centred least-squares oracle checks this definition. This removes a trend, not geological drift knowledge. Do not subtract another mean inside response removal: `zero_mean=False`.

Time taper is the pinned ObsPy quarter-cosine/SAC taper (`taper=True`, `taper_fraction=p`). Set q=floor(Np/2+0.5). With this lane's N and p, q>=1 and2q<N. Define

$$w_n=\begin{cases}\sin(\pi n/(2q)),&0\le n\le q,\\1,&q<n<N-1-q,\\\sin(\pi(N-1-n)/(2q)),&N-1-q\le n<N.\end{cases}$$

p is the total two-end fraction; it is not5% at each end when p=.05. Save actual w and compare it with [ObsPy 1.4.2 cosine_taper](https://raw.githubusercontent.com/obspy/obspy/1.4.2/obspy/signal/invsim.py). Do not silently replace it with Hann or scipy Tukey. Detrending/tapering changes amplitudes near ends; raw counts remain immutable.

## 3. Full response and regularized native motion

Full response is obtained from the uniquely selected, fully validated linear stage chain, including its declared gain normalization and digital decimation/delay/correction. For an analogue poles/zeros stage, the unnormalized factor is

$$P_j(s)=A_{0,j}\frac{\prod_l(s-z_{jl})}{\prod_l(s-p_{jl})},\qquad s=i2\pi f\ \text{for rad/s poles and zeros}.$$

Hz poles/zeros use s=if with their declared convention. Digital stages use z=exp(i2pi f/fs_stage), their polynomial/FIR coefficients and stage sampling rates. Evalresp's normalization at declared gain frequencies, not a naive product of total sensitivity twice, produces H_c(f) in counts per native unit. The [FDSN response guidance](https://docs.fdsn.org/projects/stationxml/en/latest/response.html) and [pinned ObsPy response engine](https://raw.githubusercontent.com/obspy/obspy/1.4.2/obspy/core/inventory/response.py) motivate whole-chain validation. Preserve phase, including signs/time delays; no fitted response, ignored warning or assumed missing gain.

Choose K using the pinned engine `_npts2nfft(N)`: even length at least2N, bounded by131072 in this lane; it may choose a nearby factorable number, not always a power of two. Record actual K and engine helper identity. [Pinned FFT sizing source](https://raw.githubusercontent.com/obspy/obspy/1.4.2/obspy/signal/util.py) is the specification. With f_k=k fs/K,

$$D_k=\sum_{n=0}^{N-1}w_n x_n e^{-i2\pi kn/K}.$$

Let the four prefilter corners be a<b<c<d in Hz. At each actual FFT bin,

$$T(f)=\begin{cases}0,&f\le a\ \text{or}\ f\ge d,\\\tfrac12[1-\cos(\pi(f-a)/(b-a))],&a<f<b,\\1,&b\le f\le c,\\\tfrac12[1+\cos(\pi(f-c)/(d-c))],&c<f<d.\end{cases}$$

For water level v dB, define A=max_k|H_k| and lambda=A*10^(-v/20). For nonzero H, G_k=exp(-i arg H_k)/max(|H_k|,lambda); if H=0, G=0. With v=null, G=1/H on nonzero bins and G_0=0. Require finite H and nonzero H everywhere T>0; a zero outside support is excluded, never replaced with invented response. Floor active bin count/fraction, lambda, A and inverse magnitudes are recorded. The floor preserves response phase while limiting inverse magnitude; it is not a Tikhonov posterior or a noise covariance.

For null water level, require finite nonzero H and finite1/H at ALL non-DC bins, including T=0 bins, because the pinned engine reciprocates them unconditionally. Finite-floor zero bins outside support are allowed with G=0. Undefined intermediate or native warning keeps QC-only, never a nan-to-zero repair. Check the integer W<=20000000 from contracts before response evaluation; W is not measured CPU.

$$\widehat Q_k=D_k T(f_k)G_k,\qquad \widehat q_n=\operatorname{irfft}_K(\widehat Q)_n,\quad 0\le n<N.$$

DC and Nyquist products are zero under the strict prefilter bounds. The IRFFT carries NumPy's1/K normalization; do not multiply by dt or fs again. Actual implementation uses a private Trace with the selected response attached, `remove_response(output=native_code, pre_filt=..., water_level=..., zero_mean=False, taper=True, taper_fraction=p)`. Audit the returned result against the recorded operator above and an independent small-N direct DFT oracle. A scalar sensitivity divide is not an acceptable substitute. Choice of native DISP/VEL/ACC avoids hidden integration/differentiation into a different instrument quantity. [ObsPy removal API](https://docs.obspy.org/packages/autogen/obspy.core.trace.Trace.remove_response.html) explicitly cautions about output quantity and stabilization.

The result estimates band-limited motion conditional on published response, stationarity, recorded gains, source clock and filtering. No response covariance, clock sigma or instrument recalibration is invented. Wrong epoch or gain can yield plausible-looking amplitudes: negative tests must catch it, not use fit appearance as admission.

## 4. Offline filter and edge eligibility

Compute `butter(order, [lo,hi], btype='bandpass', fs=fs, output='sos')`; each SOS row has normalized denominator a0=1. The order is the low-pass prototype order; the bandpass has twice that order. Apply `sosfiltfilt(sos,q,padtype='odd',padlen=P)`, with

$$P=3\{2J+1-\min[\#(b_2=0),\#(a_2=0)]\},$$

J is the number of SOS sections. Reject N<=P+1 instead of shortening padding. The [SciPy 1.15.2 Butterworth](https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.signal.butter.html) and [SOS forward-backward contract](https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.signal.sosfiltfilt.html) specify this engine. In the interior the combined filter response is |B(exp(i2pi f/fs))|^2 with zero phase, not the single-pass B and not amplitude |B|. The finite-record odd extension is a boundary assumption; the filter is acausal and can create pre-arrival energy.

Let L=ceil(lta_s*fs). Effective edge guard in samples is

$$g=\max(q,\lceil2fs/b\rceil,L+P,\lceil\text{edge_guard_s}\,fs\rceil).$$

Only indices g<=n<N-g are edge-valid; the requested analysis interval must lie wholly inside them and meet its minimum duration. Report g, lost samples and the actual filtered impulse/operator tail diagnostic: circular lag ell uses min(k,K-k), and the energy fraction of irfft(TG|B|^2) beyond g is recorded. This is a diagnostic, not proof of negligible unknown signal outside the recording. No universal transient guarantee or real-time arrival accuracy follows from this guard. Analysis outside the valid region is a contract failure, not a silently shortened plot.

## 5. PSD and dimensional checks

For the same edge-valid analysis samples of raw counts, native corrected motion and filtered motion, compute Welch separately. Use submitted power-of-two M, overlap M/2, hop M/2, `nfft=M`, `detrend='constant'`, `scaling='density'`, `return_onesided=True`, `average='mean'`. Explicit periodic Hann vector v_j=.5-.5cos(2pi j/M), U=sum_j v_j^2, not a library-dependent string alias. No automatic shorter segment, logarithm, epsilon offset or zero-padding.

For segment l, X_lk=sum_j v_j(y_lj-mean(y_l))exp(-i2pi kj/M). With J complete segments and gamma=1 at DC/Nyquist,2 elsewhere,

$$P_k=\frac{\gamma_k}{JfsU}\sum_{l=1}^{J}|X_{lk}|^2,\qquad \Delta f=fs/M.$$

P has units counts2/Hz, m2/Hz, (m/s)2/Hz or (m/s2)2/Hz according to its input. Integrated power=sum_k P_k delta f equals average window-weighted detrended segment energy/U; it is not automatically the variance of the full original trace. RMS is its nonnegative square root in the input unit. Save J, discarded tail count, M, U, overlap, frequency spacing and units. Discarded incomplete tail remains named, not silently converted to another window. This literal estimator follows [SciPy 1.15.2 Welch](https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.signal.welch.html); a small direct DFT and discrete Parseval equality are independent oracles. No earthquake magnitude, confidence interval or independent-bin assumption is claimed.

## 6. Classical candidate intervals, not phase labels

Use filtered native samples per channel. To avoid overflow without altering the physical arrays, internally divide by maximum absolute amplitude over the full conditioning trace; an all-zero filtered trace yields no candidates and explicit `zero_filtered_signal`. Let z_n be that dimensionless internal signal. S=ceil(sta_s fs), L=ceil(lta_s fs); require2<=S<L and N>=3L. For n>=L-1,

$$E_S[n]=S^{-1}\sum_{j=n-S+1}^n z_j^2,\quad E_L[n]=L^{-1}\sum_{j=n-L+1}^n z_j^2,\quad r_n=E_S[n]/\max(E_L[n],\operatorname{tiny}_{64}).$$

r_n=0 before L-1. Use exactly ObsPy1.4.2 `classic_sta_lta_py`, the squared-amplitude cumulative-sum engine, checked independently against direct window sums. Do not implicitly substitute its C or recursive variant. Metadata records the internal amplitude scale; ratio is dimensionless, not probability. [Pinned classical source](https://raw.githubusercontent.com/obspy/obspy/1.4.2/obspy/signal/trigger.py) is an engine reference, not the independent oracle. CF must be finite/nonnegative; invalid numerical cancellation yields retained `failed`/`numerical_failed`, not a clipped ratio or fabricated onset.

Within the requested edge-valid analysis interval [i0,i1), begin inactive. An interval starts at the first n with r_n>threshold_on while inactive and outside refractory time. It ends at the first later n with r_n<=threshold_off, with that off sample excluded. Track the earliest maximum r within the active interval. If active at i1, off=i1 and truncated=true. Refractory lasts ceil(refractory_s fs) samples after closure; no silent maximum-duration splitting. If the first analysis sample is already above threshold, retain a truncated-start flag and suppress its onset comparison (onset began before the window). Store sample/UTC/time-origin identities. Strict greater/less equality and terminal closure are tested explicitly.

Candidates retain `phase=null` and `timing_sigma_s=null`; sampling spacing1/fs is resolution, not a standard deviation. No first crossing=P or later crossing=S, no cross-channel voting that invents a missing component, no catalogue-conditioned detector. Response/filter choices influence candidates; acausality, event coda and noise can cause late/early/false/missing candidates. Nominal thresholds are user inputs, not calibrated constants or field promises.

## 7. Sealed-reference evaluation and M13 separation

Only after sealing all prediction/array hashes may the separate evaluator read analyst references. Fixed tolerance is0.5 seconds, descriptive comparability with existing held-out summaries, not a target obtained by retuning this case. Reject ambiguous reference duplicates; retain missing/ineligible/out-of-window references with named denominators. Source analyst quality codes are not converted to sigma. For the exact NSLC, references are sorted by pick UTC then source_record_id; choose the nearest unused nontruncated candidate within tolerance, ties by earliest candidate on_index. This explicitly greedy, one-to-one policy is deterministic, not an optimal assignment or phase classifier. A candidate cannot match both P and S references.

Residual e=t_candidate-t_reference, positive means later. Report every matched/unmatched row, signed residual, sample interval, median absolute error over matched rows (null if none), matched/reference fraction with denominator and unmatched candidate count. Phase in reference rows is an analyst tag only. Do not advertise per-phase prediction F1, a calibrated confidence interval or good accuracy from matched rows alone. QC failures remain in the case inventory; none are replaced by new successful selections. Reference-window access cannot change any candidate or byte hash.

Existing M08/M13 held-out metrics/checkpoint/splits remain source-pinned and read-only. This new method is not retroactively measured on that cohort. If later requested, a separate approved locked event/station-disjoint study must run both algorithms on compatible identical raw counts, preserve all exclusions and restrict model input to its original normalization/frame; response-corrected Ridgecrest values are not M13 input. [PhaseNet](https://arxiv.org/abs/1803.03211) and [cross-domain picker evaluation](https://arxiv.org/abs/2110.13671) justify a separate domain-transfer question, not a transfer/calibration PASS here.
