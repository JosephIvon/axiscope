%% Load and process data
clear;
p0 = 'Settings\CableActuatorTestbed.xml';
settings = readstruct(p0);

p1 = 'Data\Velocity_based\';
p1d = natsortfiles(dir(p1),[],'rmdot');
p1d = p1d([p1d(:).isdir]);
ob_g = cell(length(p1d),1);
ob_m = ob_g;

VarNames = {
    't', ...
    'f_load', ...
    'power_load', ...
    'power_test', ...
    'v_asco_enc', ...
    'v_asco', ...
    'asco_rate', ...
    'p_asco_enc', ...
    'p_asco', ...    
    'fno', ...
    'mfw', ...
    'trig_scope', ...
    'trig_record', ...
    'trig_export', ...
    't_test', ...
    't_load', ...
    'v_diff_enc', ...
    'v_test_tar', ...
    'v_test', ...
    'v_load_tar', ...
    'v_load', ...
    'p_diff_enc', ...
    'p_load', ...
    'p_test', ...
    'p_test_tar', ...
    'p_load_tar', ...
    'f_diff', ...
    'f_colinear', ...
    'f_orthogonal', ...
    'f_test', ...
    'f_tar', ...
    'p_lsv_enc', ...
    'v_lsv_enc'
};

for iF=1:length(p1d)
    ob_g{iF} = catanalyze(fullfile(p1,p1d(iF).name),VarNames, 'Unwind', settings);
    ob_m{iF} = catanalyze(fullfile(p1,p1d(iF).name),VarNames, 'Rewind', settings);
end

p2 = 'Data\Torque_based\';
p2d = natsortfiles(dir(p2),[],'rmdot');
p2d = p2d([p2d(:).isdir]);
tb_g = cell(length(p2d),1);
tb_m = tb_g;

for iF=1:length(p2d)
    tb_g{iF} = catanalyze(fullfile(p2,p2d(iF).name),VarNames, 'Unwind', settings);
    tb_m{iF} = catanalyze(fullfile(p2,p2d(iF).name),VarNames, 'Rewind', settings);
end

%% Plot paper: Settings
bm1 = brewermap(5, '+Blues');
bm2 = brewermap(5, '+Greens');
bm3 = brewermap(5, '+Reds');
bm = vertcat(...
    bm1(3:end,:), ...
    bm2(3:end,:), ...
    bm3(3:end,:) ...
    );
w = 100;
b = (1/w)*ones(1,w);
nMeas = length(ob_m);
p = zeros(nMeas,1);

%% Plot: Cable robot path
p3 = 'experiments\2023-05-23_WGTL_Paper\Data\Cablerobot_profile\cablerobot_profile.csv';
crp = readmatrix(p3,'NumHeaderLines',13);

close all;
fig7 = figure('Units', 'centimeters', 'Position', [5 5 8.17 4.5],'Color','w');
tiledlayout(2,1, 'Padding', 'none', 'TileSpacing', 'compact');

% Position
nexttile
hold on;
p(1) = plot(crp(:,3)./1000, crp(:,4),'Color', bm(3,:),'DisplayName','cable length');
hold off;
grid on;
xlim([0 17]);
% ylim([-8, 8.5]);
ylabel('$l$ /m','interpreter','latex');
set(gca,'FontSize',8,'FontName','Times New Roman');
leg = legend(p(1),'Location', 'northeast');
leg.ItemTokenSize = [6, 6];


% Force
nexttile
hold on;
p(2) = plot(crp(:,1)./1000, crp(:,2),'Color', bm(9,:),'DisplayName','cable force');
hold off;
grid on;
xlim([0 17]);
% ylim([-8, 8.5]);
xlabel('$t$ /s','interpreter','latex')
ylabel('$f$ /N','interpreter','latex');
set(gca,'FontSize',8,'FontName','Times New Roman');
leg = legend(p(2),'Location', 'northeast');
leg.ItemTokenSize = [6, 6];
exportgraphics(fig7,'01_winch_profiles.png','Resolution',600)

%% Plot: Std_mean
% Precompute
dl_tb_m = zeros(3,3);
dl_tb_g = zeros(3,3);
dl_ob_m = zeros(3,3);
dl_ob_g = zeros(3,3);
fr_tb_m = zeros(3,3);
fr_tb_g = zeros(3,3);
fr_ob_m = zeros(3,3);
fr_ob_g = zeros(3,3);
fc_tb_m = zeros(3,3);
fc_tb_g = zeros(3,3);
fc_ob_m = zeros(3,3);
fc_ob_g = zeros(3,3);

for iF=1:3
    for iV=1:3
        dl_tb_m(iV,iF) = tb_m{iF*iV}.p_diff_lsv.Std_mean*1000;
        dl_tb_g(iV,iF) = tb_g{iF*iV}.p_diff_lsv.Std_mean*1000;
        dl_ob_m(iV,iF) = ob_m{iF*iV}.p_diff_lsv.Std_mean*1000;
        dl_ob_g(iV,iF) = ob_g{iF*iV}.p_diff_lsv.Std_mean*1000;
        
        fr_tb_m(iV,iF) = tb_m{iF*iV}.f_fric_total.Std_mean;
        fr_tb_g(iV,iF) = tb_g{iF*iV}.f_fric_total.Std_mean;
        fr_ob_m(iV,iF) = ob_m{iF*iV}.f_fric_total.Std_mean;
        fr_ob_g(iV,iF) = ob_g{iF*iV}.f_fric_total.Std_mean;

        fc_tb_m(iV,iF) = mean(std((tb_m{iF*iV}.f_test.Measurements-tb_m{iF*iV}.f_tar.Measurements),0,1));
        fc_tb_g(iV,iF) = mean(std((tb_g{iF*iV}.f_test.Measurements-tb_g{iF*iV}.f_tar.Measurements),0,1));
        fc_ob_m(iV,iF) = mean(std((ob_m{iF*iV}.f_test.Measurements-ob_m{iF*iV}.f_tar.Measurements),0,1));
        fc_ob_g(iV,iF) = mean(std((ob_g{iF*iV}.f_test.Measurements-ob_g{iF*iV}.f_tar.Measurements),0,1));
    end
end

Ny = [0, 0, 0];
Ay = [dl_ob_m; dl_ob_g; dl_tb_m; dl_tb_g];
By = [fr_ob_m; fr_ob_g; fr_tb_m; fr_tb_g];
Cy = [fc_ob_m; fc_ob_g; fc_tb_m; fc_tb_g];

% Schlupf
close all;
fig6 = figure('Units', 'centimeters', 'Position', [5 5 8.17 7.5],'Color','w');
tiledlayout(3,1, 'Padding', 'none', 'TileSpacing', 'compact');
nexttile
A = bar(Ay);
grid on;
ylim([0 1.7]);


for iF = 1:4
    A(1).FaceColor = 'flat';
    A(1).CData(iF*3-2,:) = bm(1,:);
    A(2).FaceColor = 'flat';
    A(2).CData(iF*3-2,:) = bm(2,:);
    A(3).FaceColor = 'flat';
    A(3).CData(iF*3-2,:) = bm(3,:);

    A(1).FaceColor = 'flat';
    A(1).CData(iF*3-1,:) = bm(4,:);
    A(2).FaceColor = 'flat';
    A(2).CData(iF*3-1,:) = bm(5,:);
    A(3).FaceColor = 'flat';
    A(3).CData(iF*3-1,:) = bm(6,:);

    A(1).FaceColor = 'flat';
    A(1).CData(iF*3,:) = bm(7,:);
    A(2).FaceColor = 'flat';
    A(2).CData(iF*3,:) = bm(8,:);
    A(3).FaceColor = 'flat';
    A(3).CData(iF*3,:) = bm(9,:);
end

A(1).FaceColor = 'flat';
A(1).CData(iF*3-2,:) = bm(1,:);
A(2).FaceColor = 'flat';
A(2).CData(iF*3-2,:) = bm(2,:);
A(3).FaceColor = 'flat';
A(3).CData(iF*3-2,:) = bm(3,:);



xticklabels([70, 125, 180, 70, 125, 180, 70, 125, 180, 70, 125, 180]);
yticks([0,0.5,1,1.5])
ylabel('$\bar \sigma (\Delta l_{\mathrm{S}})$ /mm','interpreter','latex');
set(gca,'FontSize',8,'FontName','Times New Roman');
leg = legend('0.5m/s','2m/s','5m/s','Location','northoutside','NumColumns',3,'Box','off');
leg.ItemTokenSize = [6, 6];

% Reibung
nexttile
B = bar(By);
grid on;
ylim([0 12]);

for iF = 1:4
    B(1).FaceColor = 'flat';
    B(1).CData(iF*3-2,:) = bm(1,:);
    B(2).FaceColor = 'flat';
    B(2).CData(iF*3-2,:) = bm(2,:);
    B(3).FaceColor = 'flat';
    B(3).CData(iF*3-2,:) = bm(3,:);

    B(1).FaceColor = 'flat';
    B(1).CData(iF*3-1,:) = bm(4,:);
    B(2).FaceColor = 'flat';
    B(2).CData(iF*3-1,:) = bm(5,:);
    B(3).FaceColor = 'flat';
    B(3).CData(iF*3-1,:) = bm(6,:);

    B(1).FaceColor = 'flat';
    B(1).CData(iF*3,:) = bm(7,:);
    B(2).FaceColor = 'flat';
    B(2).CData(iF*3,:) = bm(8,:);
    B(3).FaceColor = 'flat';
    B(3).CData(iF*3,:) = bm(9,:);
end

xticklabels([70, 125, 180, 70, 125, 180, 70, 125, 180, 70, 125, 180]);
ylabel('$\bar \sigma (f_{\mathrm{R,Total}})$ /N','interpreter','latex');
set(gca,'FontSize',8,'FontName','Times New Roman');

% Seilkraft
nexttile
C = bar(Cy);
grid on;
ylim([0 7]);

for iF = 1:4
    C(1).FaceColor = 'flat';
    C(1).CData(iF*3-2,:) = bm(1,:);
    C(2).FaceColor = 'flat';
    C(2).CData(iF*3-2,:) = bm(2,:);
    C(3).FaceColor = 'flat';
    C(3).CData(iF*3-2,:) = bm(3,:);

    C(1).FaceColor = 'flat';
    C(1).CData(iF*3-1,:) = bm(4,:);
    C(2).FaceColor = 'flat';
    C(2).CData(iF*3-1,:) = bm(5,:);
    C(3).FaceColor = 'flat';
    C(3).CData(iF*3-1,:) = bm(6,:);

    C(1).FaceColor = 'flat';
    C(1).CData(iF*3,:) = bm(7,:);
    C(2).FaceColor = 'flat';
    C(2).CData(iF*3,:) = bm(8,:);
    C(3).FaceColor = 'flat';
    C(3).CData(iF*3,:) = bm(9,:);
end

xticklabels([70, 125, 180, 70, 125, 180, 70, 125, 180, 70, 125, 180]);
yticks([1,3,5]);
xlabel('$f_{\mathrm{d}}$ /N','interpreter','latex');
ylabel('$\bar \sigma (e_{f})$ /N','interpreter','latex');
set(gca,'FontSize',8,'FontName','Times New Roman');

exportgraphics(fig6,'Mean_Std.png','Resolution',600)


%% Plot: Slip (drehzahlbasiert)
close all;
fig1 = figure('Units', 'centimeters', 'Position', [5 5 8.17 7.5],'Color','w');
tiledlayout(2,1, 'Padding', 'none', 'TileSpacing', 'compact');

% Position
nexttile
hold on;
for iM=1:nMeas
    dispn = ['[',num2str(ob_g{iM}.f_tar.Mean_mean), 'N, ',  ...
            num2str(round(ob_g{iM}.v_test_tar.Mean_mean,1)), 'm/s]'];

    p(iM) = plot(ob_m{iM}.p_test_tar.Mean, ob_m{iM}.p_diff_lsv.Mean*1000,['-' ...
        ''],'Color', bm(iM,:),'DisplayName',dispn);
    plot(ob_g{iM}.p_test_tar.Mean, ob_g{iM}.p_diff_lsv.Mean*1000,':x', ...
        'Color', bm(iM,:), ...
        'MarkerIndices',1:(length(ob_m{iM}.p_test_tar.Mean)/10):length(ob_m{iM}.p_test_tar.Mean),...
        'DisplayName',dispn);

end
p(iM+1) = plot([0 0],[0 0], 'k-', 'DisplayName', 'rewind');
p(iM+2) = plot([0 0],[0 0], 'k:', 'DisplayName', 'unwind');
hold off;
grid on;
xlim([0 10]);
ylim([-8, 8.5]);
ylabel('$\Delta l_{\mathrm{S}}$ /mm','interpreter','latex');
set(gca,'FontSize',8,'FontName','Times New Roman');
leg = legend(p,'Location', 'northoutside','NumColumns',4,'Box','off');
leg.ItemTokenSize = [6, 6];

% Velocity
nexttile
hold on;
for iM=1:nMeas
    dispn = ['[',num2str(ob_g{iM}.f_tar.Mean_mean), 'N, ',  ...
            num2str(round(ob_g{iM}.v_test_tar.Mean_mean,1)), 'm/s]'];
    plot(ob_m{iM}.p_test_tar.Mean, ...
        filtfilt(b, 1, ob_m{iM}.v_test_tar.Mean-ob_m{iM}.v_test.Mean)*1000,...
        '-','Color', bm(iM,:),'DisplayName',dispn);
end
hold off;
grid on;
xlim([0 10]);
ylim([-3 3]);
xlabel('$l_{\mathrm{d}}$ /m','interpreter','latex');
ylabel('$e_{\mathrm{\omega}}$ /mm/s','interpreter','latex');
set(gca,'FontSize',8,'FontName','Times New Roman');
exportgraphics(fig1,'Drehzahlbasiert.png','Resolution',600)


%% Plot: Slip (drehmomentbasiert)
close all;
fig2 = figure('Units', 'centimeters', 'Position', [5 5 8.17 7.5],'Color','w');
tiledlayout(2,1, 'Padding', 'none', 'TileSpacing', 'compact');

% Position
nexttile
hold on;
for iM=1:nMeas
    dispn = ['[',num2str(ob_g{iM}.f_tar.Mean_mean), 'N, ', ...
            num2str(round(ob_g{iM}.v_test_tar.Mean_mean,1)), 'm/s]'];

    p(iM) = plot(tb_m{iM}.p_test_tar.Mean, tb_m{iM}.p_diff_lsv.Mean*1000,['-' ...
        ''],'Color', bm(iM,:),'DisplayName',dispn);
    plot(tb_g{iM}.p_test_tar.Mean, tb_g{iM}.p_diff_lsv.Mean*1000,':x', ...
        'Color', bm(iM,:), ...
        'MarkerIndices',1:(length(tb_g{iM}.p_test_tar.Mean)/10):length(tb_g{iM}.p_test_tar.Mean),...
        'DisplayName',dispn);
end
p(iM+1) = plot([0 0],[0 0], 'k-', 'DisplayName', 'rewind');
p(iM+2) = plot([0 0],[0 0], 'k:', 'DisplayName', 'unwind');
hold off;
grid on;
xlim([0 10]);
ylim([-8, 8.5]);
ylabel('$\Delta l_{\mathrm{S}}$ /mm','interpreter','latex');
set(gca,'FontSize',8,'FontName','Times New Roman');
leg = legend(p,'Location', 'northoutside','NumColumns',4,'Box','off');
leg.ItemTokenSize = [6, 6];



% Velocity
nexttile
hold on;
for iM=1:nMeas
    dispn = ['[',num2str(ob_g{iM}.f_tar.Mean_mean), 'N, ',  ...
            num2str(round(ob_g{iM}.v_test_tar.Mean_mean,1)), 'm/s]'];
    plot(tb_m{iM}.p_test_tar.Mean, ...
        filtfilt(b, 1, tb_m{iM}.v_test_tar.Mean-tb_m{iM}.v_test.Mean)*1000,...
        '-','Color', bm(iM,:),'DisplayName',dispn);
end
hold off;
grid on;
xlim([0 10]);
ylim([-3 3]);
xlabel('$l_{\mathrm{d}}$ /m','interpreter','latex');
ylabel('$e_{\mathrm{\omega}}$ /mm/s','interpreter','latex');
set(gca,'FontSize',8,'FontName','Times New Roman');
exportgraphics(fig2,'Drehmomentbasiert.png','Resolution',600)

%% Plot: Friction and efficiency factor (drehmomentbasiert)
% Precomputation
nMRows = 3;
v_interp= linspace(0,5,10);
f_interp=linspace(0,180,10);

% Precompute friction
f_fric_total = zeros(nMRows,3,2);
f_fric_test = zeros(nMRows,3,2);
f_fric_load = zeros(nMRows,3,2);
v = zeros(nMRows,3,2);

for iM = 1:nMRows
    f_fric_total(iM,1,1) = tb_m{iM*3-2}.f_fric_total.Mean_mean;
    f_fric_total(iM,2,1) = tb_m{iM*3-1}.f_fric_total.Mean_mean;
    f_fric_total(iM,3,1) = tb_m{iM*3}.f_fric_total.Mean_mean;

    f_fric_test(iM,1,1) = tb_m{iM*3-2}.f_fric_test.Mean_mean;
    f_fric_test(iM,2,1) = tb_m{iM*3-1}.f_fric_test.Mean_mean;
    f_fric_test(iM,3,1) = tb_m{iM*3}.f_fric_test.Mean_mean;

    f_fric_load(iM,1,1) = tb_m{iM*3-2}.f_fric_load.Mean_mean;
    f_fric_load(iM,2,1) = tb_m{iM*3-1}.f_fric_load.Mean_mean;
    f_fric_load(iM,3,1) = tb_m{iM*3}.f_fric_load.Mean_mean;

    f_fric_total(iM,1,2) = tb_g{iM*3-2}.f_fric_total.Mean_mean;
    f_fric_total(iM,2,2) = tb_g{iM*3-1}.f_fric_total.Mean_mean;
    f_fric_total(iM,3,2) = tb_g{iM*3}.f_fric_total.Mean_mean;

    f_fric_test(iM,1,2) = tb_g{iM*3-2}.f_fric_test.Mean_mean;
    f_fric_test(iM,2,2) = tb_g{iM*3-1}.f_fric_test.Mean_mean;
    f_fric_test(iM,3,2) = tb_g{iM*3}.f_fric_test.Mean_mean;

    f_fric_load(iM,1,2) = tb_g{iM*3-2}.f_fric_load.Mean_mean;
    f_fric_load(iM,2,2) = tb_g{iM*3-1}.f_fric_load.Mean_mean;
    f_fric_load(iM,3,2) = tb_g{iM*3}.f_fric_load.Mean_mean;

    v(iM,1,1) = abs(tb_m{iM*3-2}.v_lsv_enc.Mean_mean);
    v(iM,2,1) = abs(tb_m{iM*3-1}.v_lsv_enc.Mean_mean);
    v(iM,3,1) = abs(tb_m{iM*3}.v_lsv_enc.Mean_mean);

    v(iM,1,2) = abs(tb_g{iM*3-2}.v_lsv_enc.Mean_mean);
    v(iM,2,2) = abs(tb_g{iM*3-1}.v_lsv_enc.Mean_mean);
    v(iM,3,2) = abs(tb_g{iM*3}.v_lsv_enc.Mean_mean);


    f_m_total(iM,:) = spline(v(iM,:,1),f_fric_total(iM,:,1),v_interp);
    f_m_test(iM,:) = spline(v(iM,:,1),f_fric_test(iM,:,1),v_interp);
    f_m_load(iM,:) = spline(v(iM,:,1),f_fric_load(iM,:,1),v_interp);
    
    f_g_total(iM,:) = spline(v(iM,:,2),f_fric_total(iM,:,2),v_interp);
    f_g_test(iM,:) = spline(v(iM,:,2),f_fric_test(iM,:,2),v_interp);
    f_g_load(iM,:) = spline(v(iM,:,2),f_fric_load(iM,:,2),v_interp);
end


% Precompute efficiency factor
eff = zeros(nMRows,3,2);
feff = zeros(nMRows,3,2);
for iM = 1:nMRows
    eff(iM,1,1) = tb_m{iM*3-2}.eff_total.Mean_mean.*100;
    eff(iM,2,1) = tb_m{iM*3-1}.eff_total.Mean_mean.*100;
    eff(iM,3,1) = tb_m{iM*3}.eff_total.Mean_mean.*100;

    feff(iM,1,1) = tb_m{iM*3-2}.f_test.Mean_mean;
    feff(iM,2,1) = tb_m{iM*3-1}.f_test.Mean_mean;
    feff(iM,3,1) = tb_m{iM*3}.f_test.Mean_mean;
    
    
    eff(iM,1,2) = tb_g{iM*3-2}.eff_total.Mean_mean.*100;
    eff(iM,2,2) = tb_g{iM*3-1}.eff_total.Mean_mean.*100;
    eff(iM,3,2) = tb_g{iM*3}.eff_total.Mean_mean.*100;

    feff(iM,1,2) = tb_g{iM*3-2}.f_test.Mean_mean;
    feff(iM,2,2) = tb_g{iM*3-1}.f_test.Mean_mean;
    feff(iM,3,2) = tb_g{iM*3}.f_test.Mean_mean;
end

for iM=1:nMRows
    eff_m(iM,:) = spline(feff(:,iM,1),eff(:,iM,1),f_interp);
    eff_g(iM,:) = spline(feff(:,iM,2),eff(:,iM,2),f_interp);
end


% Plot
close all;
p = zeros(nMRows,1);
fig3 = figure('Units', 'centimeters', 'Position', [5 5 8.17 7.5],'Color','w');
tiledlayout(2,1, 'Padding', 'none', 'TileSpacing', 'compact');

% Friction
nexttile
hold on;
for iM=1:nMRows
    dispn1 = 'f_{R,Total}';
    dispn2 = 'f_{R,T}';
    dispn3 = 'f_{R,L}';
    dispn = '-';

    p(1) = plot(-v_interp, -f_m_total(iM,:),'-','Color', bm(iM+6,:),'DisplayName',dispn1);
    p(2) = plot(-v_interp, -f_m_test(iM,:),'-','Color', bm(iM,:),'DisplayName',dispn2);
    p(3) = plot(-v_interp, -f_m_load(iM,:),'-','Color', bm(iM+3,:),'DisplayName',dispn3);
    
    plot(-v(iM,1,1), -f_fric_total(iM,1,1),'o','Color', bm(iM+6,:),'MarkerSize',3,'DisplayName',dispn);
    plot(-v(iM,2,1), -f_fric_total(iM,2,1),'o','Color', bm(iM+6,:),'MarkerSize',3,'DisplayName',dispn);
    plot(-v(iM,3,1), -f_fric_total(iM,3,1),'o','Color', bm(iM+6,:),'MarkerSize',3,'DisplayName',dispn);

    plot(-v(iM,1,1), -f_fric_test(iM,1,1),'o','Color', bm(iM,:),'MarkerSize',3,'DisplayName',dispn);
    plot(-v(iM,2,1), -f_fric_test(iM,2,1),'o','Color', bm(iM,:),'MarkerSize',3,'DisplayName',dispn);
    plot(-v(iM,3,1), -f_fric_test(iM,3,1),'o','Color', bm(iM,:),'MarkerSize',3,'DisplayName',dispn);

    plot(-v(iM,1,1), -f_fric_load(iM,1,1),'o','Color', bm(iM+3,:),'MarkerSize',3,'DisplayName',dispn);
    plot(-v(iM,2,1), -f_fric_load(iM,2,1),'o','Color', bm(iM+3,:),'MarkerSize',3,'DisplayName',dispn);
    plot(-v(iM,3,1), -f_fric_load(iM,3,1),'o','Color', bm(iM+3,:),'MarkerSize',3,'DisplayName',dispn);

    plot(v_interp, f_g_total(iM,:),'-','Color', bm(iM+6,:),'DisplayName',dispn);
    plot(v_interp, f_g_test(iM,:),'-','Color', bm(iM,:),'DisplayName',dispn);
    plot(v_interp, f_g_load(iM,:),'-','Color', bm(iM+3,:),'DisplayName',dispn);
    
    plot(v(iM,1,2), f_fric_total(iM,1,2),'o','Color', bm(iM+6,:),'MarkerSize',3,'DisplayName',dispn);
    plot(v(iM,2,2), f_fric_total(iM,2,2),'o','Color', bm(iM+6,:),'MarkerSize',3,'DisplayName',dispn);
    plot(v(iM,3,2), f_fric_total(iM,3,2),'o','Color', bm(iM+6,:),'MarkerSize',3,'DisplayName',dispn);

    plot(v(iM,1,2), f_fric_test(iM,1,2),'o','Color', bm(iM,:),'MarkerSize',3,'DisplayName',dispn);
    plot(v(iM,2,2), f_fric_test(iM,2,2),'o','Color', bm(iM,:),'MarkerSize',3,'DisplayName',dispn);
    plot(v(iM,3,2), f_fric_test(iM,3,2),'o','Color', bm(iM,:),'MarkerSize',3,'DisplayName',dispn);

    plot(v(iM,1,2), f_fric_load(iM,1,2),'o','Color', bm(iM+3,:),'MarkerSize',3,'DisplayName',dispn);
    plot(v(iM,2,2), f_fric_load(iM,2,2),'o','Color', bm(iM+3,:),'MarkerSize',3,'DisplayName',dispn);
    plot(v(iM,3,2), f_fric_load(iM,3,2),'o','Color', bm(iM+3,:),'MarkerSize',3,'DisplayName',dispn);
end
hold off;
grid on;
xlim([-5.1, 5.1]);
ylim([-250, 250]);
xticks([-5 -4 -3 -2 -1 0 1 2 3 4 5]);
xlabel('$\dot l$ /m/s','interpreter','latex');
ylabel('friction force /N','interpreter','latex');
set(gca,'FontSize',8,'FontName','Times New Roman');
leg = legend([p(2), p(3), p(1)],'Location', 'northwest','NumColumns',2);
leg.ItemTokenSize = [8, 8];

% Efficiency factor
nexttile
for iM=1:nMRows
    dispn = [num2str(-round(tb_m{iM}.v_test_tar.Mean_mean,1)), 'm/s'];
    p(iM) = plot(f_interp, eff_m(iM,:),'-','Color',bm(iM*3,:),'DisplayName', dispn);
    hold on;    
    plot(f_interp, eff_g(iM,:),':','Color',bm(iM*3,:),'DisplayName', dispn);

    plot(feff(iM,1,1), eff(iM,1,1),'o','Color',bm(3,:),'MarkerSize',3);
    plot(feff(iM,2,1), eff(iM,2,1),'o','Color',bm(6,:),'MarkerSize',3);
    plot(feff(iM,3,1), eff(iM,3,1),'o','Color',bm(9,:),'MarkerSize',3);
    
    plot(feff(iM,1,2), eff(iM,1,2),'o','Color',bm(3,:),'MarkerSize',3);
    plot(feff(iM,2,2), eff(iM,2,2),'o','Color',bm(6,:),'MarkerSize',3);
    plot(feff(iM,3,2), eff(iM,3,2),'o','Color',bm(9,:),'MarkerSize',3);
end
p(iM+1) = plot([0 0],[0 0], 'k-', 'DisplayName', 'rewind');
p(iM+2) = plot([0 0],[0 0], 'k:', 'DisplayName', 'unwind');
hold off;
grid on;
xlim([65 181]);
ylim([0 100]);
yticks([20 40 60 80 100]);
xlabel('$f$ /N','interpreter','latex');
ylabel('$\eta_{\mathrm{Total}}$ /\%','interpreter','latex');
set(gca,'FontSize',8,'FontName','Times New Roman');
leg = legend(p,'Location', 'north','NumColumns',5);
leg.ItemTokenSize = [6, 6];
exportgraphics(fig3,'Reibung_Wirkungsgrad.png','Resolution',600);


%Detail: friction
p = zeros(nMRows,1);
fig4 = figure('Units', 'centimeters', 'Position', [5 5 4 3],'Color','w');
hold on;
for iM=1:nMRows
    dispn = [num2str(tb_m{iM*3-2}.f_tar.Mean_mean), 'N'];

    p(iM) = plot(-v_interp, -f_m_total(iM,:),'-','Color', bm(iM+6,:),'DisplayName',dispn);
    plot(-v_interp, -f_m_test(iM,:),'-','Color', bm(iM,:),'DisplayName',dispn);
    plot(-v_interp, -f_m_load(iM,:),'-','Color', bm(iM+3,:),'DisplayName',dispn);
    
    plot(-v(iM,1,1), -f_fric_total(iM,1,1),'o','Color', bm(iM+6,:),'MarkerSize',3,'DisplayName',dispn);
    plot(-v(iM,2,1), -f_fric_total(iM,2,1),'o','Color', bm(iM+6,:),'MarkerSize',3,'DisplayName',dispn);
    plot(-v(iM,3,1), -f_fric_total(iM,3,1),'o','Color', bm(iM+6,:),'MarkerSize',3,'DisplayName',dispn);

    plot(-v(iM,1,1), -f_fric_test(iM,1,1),'o','Color', bm(iM,:),'MarkerSize',3,'DisplayName',dispn);
    plot(-v(iM,2,1), -f_fric_test(iM,2,1),'o','Color', bm(iM,:),'MarkerSize',3,'DisplayName',dispn);
    plot(-v(iM,3,1), -f_fric_test(iM,3,1),'o','Color', bm(iM,:),'MarkerSize',3,'DisplayName',dispn);

    plot(-v(iM,1,1), -f_fric_load(iM,1,1),'o','Color', bm(iM+3,:),'MarkerSize',3,'DisplayName',dispn);
    plot(-v(iM,2,1), -f_fric_load(iM,2,1),'o','Color', bm(iM+3,:),'MarkerSize',3,'DisplayName',dispn);
    plot(-v(iM,3,1), -f_fric_load(iM,3,1),'o','Color', bm(iM+3,:),'MarkerSize',3,'DisplayName',dispn);

    plot(v_interp, f_g_total(iM,:),'-','Color', bm(iM+6,:),'DisplayName',dispn);
    plot(v_interp, f_g_test(iM,:),'-','Color', bm(iM,:),'DisplayName',dispn);
    plot(v_interp, f_g_load(iM,:),'-','Color', bm(iM+3,:),'DisplayName',dispn);
    
    plot(v(iM,1,2), f_fric_total(iM,1,2),'o','Color', bm(iM+6,:),'MarkerSize',3,'DisplayName',dispn);
    plot(v(iM,2,2), f_fric_total(iM,2,2),'o','Color', bm(iM+6,:),'MarkerSize',3,'DisplayName',dispn);
    plot(v(iM,3,2), f_fric_total(iM,3,2),'o','Color', bm(iM+6,:),'MarkerSize',3,'DisplayName',dispn);

    plot(v(iM,1,2), f_fric_test(iM,1,2),'o','Color', bm(iM,:),'MarkerSize',3,'DisplayName',dispn);
    plot(v(iM,2,2), f_fric_test(iM,2,2),'o','Color', bm(iM,:),'MarkerSize',3,'DisplayName',dispn);
    plot(v(iM,3,2), f_fric_test(iM,3,2),'o','Color', bm(iM,:),'MarkerSize',3,'DisplayName',dispn);

    plot(v(iM,1,2), f_fric_load(iM,1,2),'o','Color', bm(iM+3,:),'MarkerSize',3,'DisplayName',dispn);
    plot(v(iM,2,2), f_fric_load(iM,2,2),'o','Color', bm(iM+3,:),'MarkerSize',3,'DisplayName',dispn);
    plot(v(iM,3,2), f_fric_load(iM,3,2),'o','Color', bm(iM+3,:),'MarkerSize',3,'DisplayName',dispn);

    plot(v(iM,1,2), f_fric_load(iM,1,2),'o','Color', bm(iM+3,:),'MarkerSize',3,'DisplayName',dispn);
    plot(v(iM,2,2), f_fric_load(iM,2,2),'o','Color', bm(iM+3,:),'MarkerSize',3,'DisplayName',dispn);
    plot(v(iM,3,2), f_fric_load(iM,3,2),'o','Color', bm(iM+3,:),'MarkerSize',3,'DisplayName',dispn);
end
hold off;
grid on;
xlim([1.95, 2.3]);
ylim([160, 172]);
set(gca,'FontSize',8,'FontName','Times New Roman');
leg = legend(p,'Location', 'northoutside','NumColumns',3);
leg.ItemTokenSize = [6, 6];
exportgraphics(fig4,'Reibung_Detail.png','Resolution',600);