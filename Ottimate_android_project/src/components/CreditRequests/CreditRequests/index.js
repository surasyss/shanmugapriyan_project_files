import React from 'react';
import { View } from 'react-native';
import ScrollableTabView, { DefaultTabBar } from 'react-native-scrollable-tab-view';
import Colors from '../../../styles/Colors';
import TabStyles from '../../../styles/tabStyles';
import AllCreditRequestsContainer from '../../../containers/CreditRequests/AllCreditRequestsContainer';
import AddCreditRequestContainer from '../../../containers/CreditRequests/AddCreditRequestContainer';

function CreditRequests(props) {
  const { navigation, canAddCreditRequest } = props;
  if (canAddCreditRequest) {
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
        <View tabLabel="Add Credit">
          <AddCreditRequestContainer
            navigation={navigation}
          />
        </View>
        <View tabLabel="Credit Requests">
          <AllCreditRequestsContainer
            navigation={navigation}
          />
        </View>
      </ScrollableTabView>
    );
  }

  return (
    <AllCreditRequestsContainer
      navigation={navigation}
    />
  );
}

CreditRequests.navigationOptions = () => ({
  title: 'Credit Requests'
});

export default CreditRequests;
