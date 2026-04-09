%% ============================================================
%  EEG <-> fNIRS Marker Alignment
%% ============================================================

%% --- STEP 1: Load EEG markers from XDF ---
streams = load_xdf('C:\Users\rpier12\Documents\CurrentStudy\sub-P001\ses-S001\eeg\sub-P001_ses-S001_task-Default_run-001_eeg.xdf');

eeg_times  = [];
eeg_markers = [];

for i = 1:length(streams)
    values     = streams{i}.time_series;
    timestamps = streams{i}.time_stamps;
    if size(values, 1) > 1, continue; end
    
    mask = ismember(values, [1 2 4]);
    if any(mask)
        eeg_times   = timestamps(mask);
        eeg_markers = values(mask);
        fprintf('Found marker stream in Stream %d: %s\n', i, streams{i}.info.name)
        break
    end
end

% Convert EEG LSL times to datetime using the PC clock offset
% LSL epoch is 1970-01-01 (Unix time), same as datetime epoch
eeg_datetime = datetime(eeg_times, 'ConvertFrom', 'posixtime', 'TimeZone', 'local');

%% --- STEP 2: Load fNIRS markers from .tri file ---
fid  = fopen('C:\Users\rpier12\Documents\NIRx\Data\2026-04-09\2026-04-09_003\2026-04-09_003_lsl.tri', 'r');
raw  = textscan(fid, '%s', 'Delimiter', '\n');
fclose(fid);
lines = raw{1};

fnirs_datetime = datetime([], 'ConvertFrom', 'posixtime', 'TimeZone', 'local');
fnirs_markers  = [];

for i = 1:length(lines)
    line = strtrim(lines{i});
    if isempty(line), continue; end
    parts = strsplit(line, ';');
    if length(parts) < 3, continue; end
    
    marker_val = str2double(strtrim(parts{3}));
    if ~ismember(marker_val, [1 2 4]), continue; end
    
    dt = datetime(strtrim(parts{1}), 'InputFormat', 'yyyy-MM-dd''T''HH:mm:ss.SSSSSS', 'TimeZone', 'local');
    fnirs_datetime(end+1) = dt;
    fnirs_markers(end+1)  = marker_val;
end

%% --- STEP 3: Pair markers by type and order ---

% Convert fNIRS datetimes to posixtime (seconds since 1970) for numeric comparison
fnirs_posix = posixtime(fnirs_datetime);

% Compute clock offset from first marker-1 event (same event, both streams)
eeg_idx1   = find(eeg_markers   == 1, 1);
fnirs_idx1 = find(fnirs_markers == 1, 1);
clock_offset = fnirs_posix(fnirs_idx1) - eeg_times(eeg_idx1);
fprintf('Clock offset (fNIRS posix - EEG LSL): %.4f seconds\n\n', clock_offset)

% Now align: convert all EEG LSL times to posixtime by adding offset
eeg_posix_aligned = eeg_times + clock_offset;

fprintf('====================================================\n')
fprintf(' Event | EEG Timestamp              | fNIRS Timestamp            | Diff (ms)\n')
fprintf('-------|----------------------------|----------------------------|----------\n')

all_types  = [1 2 4];
event_rows = {};

for t = 1:length(all_types)
    mtype = all_types(t);

    eeg_idx   = find(eeg_markers   == mtype);
    fnirs_idx = find(fnirs_markers == mtype);
    n_pairs   = min(length(eeg_idx), length(fnirs_idx));

    for k = 1:n_pairs
        e_posix = eeg_posix_aligned(eeg_idx(k));
        f_posix = fnirs_posix(fnirs_idx(k));

        diff_ms = (f_posix - e_posix) * 1000;

        e_dt = datetime(e_posix, 'ConvertFrom', 'posixtime', 'TimeZone', 'local');
        f_dt = fnirs_datetime(fnirs_idx(k));

        fprintf('  %d    | %s | %s | %+.2f ms\n', ...
            mtype, ...
            datestr(e_dt, 'yyyy-mm-dd HH:MM:SS.FFF'), ...
            datestr(f_dt, 'yyyy-mm-dd HH:MM:SS.FFF'), ...
            diff_ms)

        event_rows{end+1} = {mtype, e_dt, f_dt, diff_ms};
    end
end

%% --- STEP 4: Summary stats ---
all_diffs = cellfun(@(r) r{4}, event_rows);
fprintf('\n====================================================\n')
fprintf('Mean difference:   %+.2f ms\n', mean(all_diffs))
fprintf('Std deviation:     %.2f ms\n',  std(all_diffs))
fprintf('Max abs diff:      %.2f ms\n',  max(abs(all_diffs)))
