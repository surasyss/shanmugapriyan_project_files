import React from 'react';
import { View } from 'react-native';
import ScrollableTabView, { DefaultTabBar } from 'react-native-scrollable-tab-view';
import Colors from '../../../styles/Colors';
import TabStyles from '../../../styles/tabStyles';
import AllPurchasedItemsContainer from '../../../containers/PurchasedItems/AllPurchasedItemsContainer';
import StarredPurchasedItemsContainer from '../../../containers/PurchasedItems/StarredPurchasedItemsContainer';

export default function PurchasedItemsTab(props) {
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
      <View tabLabel="Starred Items">
        <StarredPurchasedItemsContainer
          navigation={navigation}
        />
      </View>
      <View tabLabel="All Items">
        <AllPurchasedItemsContainer
          navigation={navigation}
        />
      </View>
    </ScrollableTabView>
  );
}
