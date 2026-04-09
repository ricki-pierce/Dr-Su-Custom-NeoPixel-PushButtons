
% Open and read the .tri file as text
fid = fopen('C:\Users\rpier12\Documents\NIRx\Data\2026-04-09\2026-04-09_003\2026-04-09_003_lsl.tri', 'r');
raw = textscan(fid, '%s', 'Delimiter', '\n');
fclose(fid);
disp(raw{1})
