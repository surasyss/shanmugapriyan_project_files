import React from 'react';
import { View } from 'react-native';
import ScrollableTabView, { DefaultTabBar } from 'react-native-scrollable-tab-view';
import Colors from '../../../styles/Colors';
import TabStyles from '../../../styles/tabStyles';
import PendingApprovalContainer from '../../../containers/Invoices/PendingApprovalContainer';
import AllInvoicesContainer from '../../../containers/Invoices/AllInvoicesContainer';

function ApprovalInvoices(props) {
  const { navigation } = props;

  return (
    <ScrollableTabView
      style={{ marginLeft: 0 }}
      tabBarBackgroundColor={TabStyles.tabStyle.backgroundColor}
      tabBarUnderlineStyle={TabStyles.tabBarUnderlineStyle}
      tabBarInactiveTextColor={Colors.primaryLight}
      tabBarActiveTextColor={Colors.white}
      tabBarTextStyle={TabStyles.textStyle}
      initialPage={0}
      renderTabBar={() => <DefaultTabBar />}
    >
      <View tabLabel="My Approvals">
        <PendingApprovalContainer
          navigation={navigation}
        />
      </View>
      <View tabLabel="All Invoices">
        <AllInvoicesContainer
          navigation={navigation}
        />
      </View>
    </ScrollableTabView>
  );
}

ApprovalInvoices.navigationOptions = () => ({
  title: 'Invoices'
});

export default ApprovalInvoices;
