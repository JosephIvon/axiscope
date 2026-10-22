function [Exp, opts] = catcsv2cell(Path, VarNames, NumHeaderLines, SampleTime)
% TCCSV2CELL converts a TwinCAT-Scope generated CSV into a cell with user-
% defined variable names
%
% Data starts always with time vector.

%% Define csv structure
VariableNames = VarNames;

%% Read data
A = readmatrix(Path,'NumHeaderLines',NumHeaderLines);
opts = detectImportOptions(Path);

%% Initalize variables
Exp = {};
Exp.VariableNames = VariableNames;
nVar = size(Exp.VariableNames,2);

%% Convert matrix to cell
Exp.Raw.(Exp.VariableNames{1}) = A(:,1)*SampleTime;
for iD=2:nVar
    Exp.Raw.(Exp.VariableNames{iD}) = A(:,iD*2-2);
end

%% Pre-filter data with trigger
% Remove unrecorded data
for iD=1:nVar
    Exp.Data.(Exp.VariableNames{iD}) = ...
    Exp.Raw.(Exp.VariableNames{iD})(Exp.Raw.trig_record~=0);
end

% Remove NaNs
for iD=1:nVar
    Exp.Data.(Exp.VariableNames{iD}) = ...
    rmmissing(Exp.Data.(Exp.VariableNames{iD}));
end


%% Process data
% Set moving-forward indicator from 0 to -1 if moving backward
Exp.Data.mfw(Exp.Data.mfw<=0) = -1; 

% Use moving-forward indicator to set direction of encoder data
Exp.Data.v_asco_enc = Exp.Data.v_asco_enc.*Exp.Data.mfw;
Exp.Data.v_lsv_enc = Exp.Data.v_lsv_enc.*Exp.Data.mfw;


%% Zero-Offset
% Time
Exp.Data.t = Exp.Data.t(:) - Exp.Data.t(1);

% Position
Exp.Data.p_test = Exp.Data.p_test(:) - Exp.Data.p_test(1);
Exp.Data.p_load = -(Exp.Data.p_load(:) - Exp.Data.p_load(1));
Exp.Data.p_test_tar = Exp.Data.p_test_tar(:) - Exp.Data.p_test_tar(1);
Exp.Data.p_load_tar = Exp.Data.p_load_tar(:) - Exp.Data.p_load_tar(1);
Exp.Data.p_diff_enc = Exp.Data.p_diff_enc(:) - Exp.Data.p_diff_enc(1);
Exp.Data.p_asco_enc = Exp.Data.p_asco_enc(:) - Exp.Data.p_asco_enc(1);
Exp.Data.p_lsv_enc = Exp.Data.p_lsv_enc(:) - Exp.Data.p_lsv_enc(1);

end

