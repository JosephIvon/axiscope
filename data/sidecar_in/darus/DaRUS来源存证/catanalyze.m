function StatData = catanalyze(Path, VarNames, Modus, SettingsXML)
% ANALYZE CAT process data for cable actuator testrig at ISW
%   Data will be set to an equal time base and slip is computed for both
%   rewind and unwind the test winch

Path = fullfile(Path, Modus);
MeasFiles = natsortfiles(dir(fullfile(Path,'*.csv')));
nFiles = length(MeasFiles);

StatData = {};

%% Read data
% Import csv
read_data = catcsv2cell(fullfile(Path, MeasFiles(1).name),VarNames, 14, 0.001);

% Build reference vector
ref_vec = read_data.Data.t;
nData = length(ref_vec);

% Interpolate data to get same vector length
for iM = 1:nFiles
    baseFileName = MeasFiles(iM).name;
    fullFileName = fullfile(Path, baseFileName);
    read_data = catcsv2cell(fullFileName, VarNames, 14, 0.001);
    
    StatData.VariableNames = read_data.VariableNames;
    for iV = 1:length(StatData.VariableNames)
        q = read_data.Data.(StatData.VariableNames{iV});
        qt = interp1(read_data.Data.t, q, ref_vec);
        StatData.(StatData.VariableNames{iV}).Measurements(:,iM) = qt;
    end

end

% Fill NaN values
for iV = 1:length(StatData.VariableNames)
    StatData.(StatData.VariableNames{iV}).Measurements = ...
        fillmissing(StatData.(StatData.VariableNames{iV}).Measurements,'linear','SamplePoints',ref_vec);
end

%% Add additional properties
% Add to VariableNames
StatData.VariableNames{length(StatData.VariableNames)+1} = 'ft_load';
StatData.VariableNames{length(StatData.VariableNames)+1} = 'ft_test';
StatData.VariableNames{length(StatData.VariableNames)+1} = 'ft_total';
StatData.VariableNames{length(StatData.VariableNames)+1} = 'p_diff_asco';
StatData.VariableNames{length(StatData.VariableNames)+1} = 'v_diff_asco';
StatData.VariableNames{length(StatData.VariableNames)+1} = 'p_diff_lsv';
StatData.VariableNames{length(StatData.VariableNames)+1} = 'v_diff_lsv';
StatData.VariableNames{length(StatData.VariableNames)+1} = 'f_fric_total';
StatData.VariableNames{length(StatData.VariableNames)+1} = 'f_fric_load';
StatData.VariableNames{length(StatData.VariableNames)+1} = 'f_fric_test';
StatData.VariableNames{length(StatData.VariableNames)+1} = 'pin_total';
StatData.VariableNames{length(StatData.VariableNames)+1} = 'ppreload_lsv';
StatData.VariableNames{length(StatData.VariableNames)+1} = 'pout_gen';
StatData.VariableNames{length(StatData.VariableNames)+1} = 'pout_total';
StatData.VariableNames{length(StatData.VariableNames)+1} = 'ploss_total';
StatData.VariableNames{length(StatData.VariableNames)+1} = 'ploss_total2';
StatData.VariableNames{length(StatData.VariableNames)+1} = 'ploss_test';
StatData.VariableNames{length(StatData.VariableNames)+1} = 'ploss_load';
StatData.VariableNames{length(StatData.VariableNames)+1} = 'eff_total';
StatData.VariableNames{length(StatData.VariableNames)+1} = 'dist_factor';

%% Compute additional properties
% ----- ERRORS -----
% ASCOspeed diff
StatData.p_diff_asco.Measurements = ...
    StatData.p_asco_enc.Measurements - StatData.p_test.Measurements;
StatData.v_diff_asco.Measurements = ...
    StatData.v_asco_enc.Measurements - StatData.v_test.Measurements;

% LSV-2100 diff
StatData.p_diff_lsv.Measurements = ...
    StatData.p_lsv_enc.Measurements - StatData.p_test.Measurements;
StatData.v_diff_lsv.Measurements = ...
    StatData.v_lsv_enc.Measurements - StatData.v_test.Measurements;

% Zero-offset values if Modus=='Rewind'
if strcmp(Modus,'Rewind')
    for iF=1:nFiles
    % Target position
    StatData.p_test_tar.Measurements(:,iF) = ...
        StatData.p_test_tar.Measurements(:,iF) - StatData.p_test_tar.Measurements(end,iF);
    
    % Encoders diff
    StatData.p_diff_enc.Measurements(:,iF) = ...
        StatData.p_diff_enc.Measurements(:,iF)-StatData.p_diff_enc.Measurements(end,iF);

    % ASCOspeed diff
    StatData.p_diff_asco.Measurements(:,iF) = ...
        StatData.p_diff_asco.Measurements(:,iF)- StatData.p_diff_asco.Measurements(end,iF);

    % LSV-2100 diff
    StatData.p_diff_lsv.Measurements(:,iF) = ...
        StatData.p_diff_lsv.Measurements(:,iF)-StatData.p_diff_lsv.Measurements(end,iF);
    end
end

% ----- FORCES -----
% (EXPERIMENTAL: Fehler in den Drehmomenten -> Faktor 10)
% Transmission forces of test/load motor
StatData.ft_load.Measurements = StatData.t_load.Measurements .* 10 .* ...
    SettingsXML.drivesystem.winch(1).gear.ratioAttribute ./ ...
    SettingsXML.drivesystem.winch(1).drum.r_drumAttribute;

StatData.ft_test.Measurements = StatData.t_test.Measurements .* 10 ./ ...
    SettingsXML.drivesystem.winch(2).drum.r_drumAttribute;

% Overall transmission forces
StatData.ft_total.Measurements = abs(StatData.ft_load.Measurements + StatData.ft_test.Measurements);

% ----- FRICTION -----
% Overall friction
% StatData.f_fric_total.Measurements = ...
%     abs(StatData.ft_test.Measurements - StatData.ft_load.Measurements);

% Friction of test and load winch (computed with optimization)
StatData.f_fric_load.Measurements = NaN(1, nFiles);
StatData.f_fric_test.Measurements = NaN(1, nFiles);
StatData.dist_factor.Measurements = NaN(1, nFiles);

% Inital values
for iM = 1:nFiles
    % Compute overall friction
    StatData.f_fric_total.Measurements(1, iM) = ...
        abs(mean(StatData.ft_test.Measurements(:,iM)) - ...
        mean(StatData.ft_load.Measurements(:,iM)));

    % Get total friction for measuring point
    fr0 = mean(StatData.f_fric_total.Measurements(:,iM));
    
    % Set initial vector
    x0 = [fr0/2, fr0/2, 0.5];        
    
    % Set upper and lower bound
    ub = [fr0, fr0, 1];
    lb = [0, 0, 0];
    
    % Set target function
    fric_target_func = @(x) ...
        winchfriction_target( ...
        x, ...
        mean(StatData.ft_load.Measurements(:,iM)), ...
        mean(StatData.ft_test.Measurements(:,iM)), ...
        mean(StatData.f_test.Measurements(:,iM)));
    
    % Set linear inequalities
    A = [0, 2, 0];
    b = fr0;

    % Set nonlinear constraints
    fric_nonlcon = @(x) ...
        winchfriction_nonlcon( ...
        x, ...
        mean(StatData.ft_load.Measurements(:,iM)), ...
        mean(StatData.ft_test.Measurements(:,iM)));
    
    % Set optimization options
    fric_options = optimoptions(@fmincon,'Algorithm','interior-point',...
      'TolFun', 1e-08, 'TolX', 1e-08, 'MaxIter', 100000, ...
      'MaxFunEvals', 100000,'Display','none');
    
    % Execute optimization
    x_opt = fmincon(fric_target_func, x0, A, b, [], [], lb, ub, fric_nonlcon, fric_options);
    
    % Write friction load winch
    StatData.f_fric_load.Measurements(1, iM) = x_opt(1);
    
    % Write friction test winch 
    StatData.f_fric_test.Measurements(1, iM) = x_opt(2);

    % Write force distribution factor
    StatData.dist_factor.Measurements(1, iM) = x_opt(3);
end

% ----- POWER -----
% Overall input power
pmot_test = StatData.power_test.Measurements;
pmot_test(pmot_test<0) = 0;
pmot_load = StatData.power_load.Measurements;
pmot_load(pmot_load<0) = 0;
StatData.pin_total.Measurements = abs(pmot_test + pmot_load);

% Mechanical power of moving cable (LSV-2100)
StatData.ppreload_lsv.Measurements = abs(StatData.f_test.Measurements .* ...
    StatData.v_lsv_enc.Measurements);

% Generator power
pgen_test = StatData.power_test.Measurements;
pgen_test(pgen_test>0) = 0;
pgen_load = StatData.power_load.Measurements;
pgen_load(pgen_load>0) = 0;
StatData.pout_gen.Measurements = abs(pgen_test + pgen_load);

% Overall output power
StatData.pout_total.Measurements = abs(StatData.ppreload_lsv.Measurements);

% Overall power loss
StatData.ploss_total.Measurements = abs(abs(StatData.pin_total.Measurements) - ...
    abs(StatData.pout_total.Measurements));

StatData.ploss_total2.Measurements = (StatData.power_test.Measurements + ...
    StatData.power_load.Measurements) - StatData.ppreload_lsv.Measurements;

% Power loss (not implemented)
StatData.ploss_load.Measurements = NaN;
StatData.ploss_test.Measurements = NaN;


% ---- EFFICIENCY FACTOR -----
% Overall efficiency
StatData.eff_total.Measurements = abs(StatData.pout_total.Measurements) ./ ...
    abs(StatData.pin_total.Measurements);


%% Statistical analysis
for iF = 1:nFiles
    for iD = 1:length(StatData.VariableNames)
        % Means
        StatData.(StatData.VariableNames{iD}).Mean = ...
            mean(StatData.(StatData.VariableNames{iD}).Measurements, 2);
        
        % Standard deviations
        StatData.(StatData.VariableNames{iD}).Std = ...
            std(StatData.(StatData.VariableNames{iD}).Measurements, 0, 2);
        
        % Mean of means
        StatData.(StatData.VariableNames{iD}).Mean_mean = ...
            mean(StatData.(StatData.VariableNames{iD}).Mean);
        
        % Maximum of Standard deviations
        StatData.(StatData.VariableNames{iD}).Std_max = ...
            max(StatData.(StatData.VariableNames{iD}).Std);
        
        % Mean of Standard deviations
        StatData.(StatData.VariableNames{iD}).Std_mean = ...
            mean(StatData.(StatData.VariableNames{iD}).Std);
    end
end

end

