import React from 'react';
import { View } from 'react-native';
import ScrollableTabView, { DefaultTabBar } from 'react-native-scrollable-tab-view';
import Colors from '../../../styles/Colors';
import TabStyles from '../../../styles/tabStyles';
import PendingPaymentApprovalContainer from '../../../containers/Payments/PendingPaymentApprovalContainer';
import AllPaymentsContainer from '../../../containers/Payments/AllPaymentsContainer';

function ApprovalPayments(props) {
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
        <PendingPaymentApprovalContainer
          navigation={navigation}
        />
      </View>
      <View tabLabel="All Payments">
        <AllPaymentsContainer
          navigation={navigation}
        />
      </View>
    </ScrollableTabView>
  );
}

ApprovalPayments.navigationOptions = () => ({
  title: 'Payments'
});

export default ApprovalPayments;
