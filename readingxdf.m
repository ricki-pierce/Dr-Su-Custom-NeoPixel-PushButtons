streams = load_xdf('C:\Users\rpier12\Documents\CurrentStudy\sub-P001\ses-S001\eeg\sub-P001_ses-S001_task-Default_run-001_eeg.xdf');

% Print all streams so you know what's there
for i = 1:length(streams)
    fprintf('Stream %d: Name = %s | Type = %s\n', i, streams{i}.info.name, streams{i}.info.type)
end

% Automatically find all streams containing markers 1, 2, or 4
for i = 1:length(streams)
    values = streams{i}.time_series;
    timestamps = streams{i}.time_stamps;
    
    % Skip EEG streams (too many channels / values way outside 1-4)
    if size(values, 1) > 1
        continue
    end
    
    commanded = timestamps(values == 1);
    lit        = timestamps(values == 2);
    pressed    = timestamps(values == 4);
    
    % Only print streams that actually contain at least one of your markers
    if length(commanded) + length(lit) + length(pressed) > 0
        fprintf('\n--- Stream %d: %s ---\n', i, streams{i}.info.name)
        fprintf('Commanded events (1): %d\n', length(commanded))
        fprintf('Lit events       (2): %d\n', length(lit))
        fprintf('Pressed events   (4): %d\n', length(pressed))
        
        % Print each timestamp and its marker value
        fprintf('\nFull marker list:\n')
        for j = 1:length(timestamps)
            if any(values(j) == [1 2 4])
                fprintf('  Time: %.4f  |  Marker: %d\n', timestamps(j), values(j))
            end
        end
    end
end



% streams = load_xdf('C:\Users\rpier12\Documents\CurrentStudy\sub-P001\ses-S001\eeg\sub-P001_ses-S001_task-Default_run-001_eeg.xdf');
% 
% 
% for i = 1:length(streams)
%     disp(i)
%     disp(streams{i}.info.name)
%     disp(streams{i}.info.type)
% end
% 
% timestamps = trigger_stream.time_stamps;
% values     = trigger_stream.time_series;
% 
% unique_vals = unique(values);
% disp('Unique trigger values found:')
% disp(unique_vals)
% 
% % Count non-zero triggers
% nonzero = values(values ~= 0);
% fprintf('Non-zero trigger events: %d\n', length(nonzero))
% 
% marker_stream = streams{1};
% timestamps = marker_stream.time_stamps;
% values     = marker_stream.time_series;
% 
% commanded = timestamps(values == 1);
% lit        = timestamps(values == 2);
% pressed    = timestamps(values == 4);
% 
% fprintf('Commanded events: %d\n', length(commanded))
% fprintf('Lit events:       %d\n', length(lit))
% fprintf('Pressed events:   %d\n', length(pressed))

% streams = load_xdf('C:\Users\rpier12\Documents\CurrentStudy\sub-P001\ses-S001\eeg\sub-P001_ses-S001_task-Default_run-001_eeg.xdf');
% 
% for i = 1:length(streams)
%     disp(i)
%     disp(streams{i}.info.name)
%     disp(streams{i}.info.type)
% end
% 
% marker_stream = streams{4};
% 
% timestamps = marker_stream.time_stamps;
% values     = marker_stream.time_series;
% 
% % Display all markers
% for i = 1:length(timestamps)
%     fprintf('Time: %.4f  |  Marker: %s\n', timestamps(i), num2str(values(i)));
% end
% 
% commanded = timestamps(values == 1);   % Button told to light
% lit        = timestamps(values == 2);   % Button confirmed lit
% pressed    = timestamps(values == 4);   % Button pressed
% 
% fprintf('Commanded events: %d\n', length(commanded))
% fprintf('Lit events:       %d\n', length(lit))
% fprintf('Pressed events:   %d\n', length(pressed))
