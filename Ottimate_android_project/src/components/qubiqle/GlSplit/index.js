import React from 'react';
import { Text, View, Image } from 'react-native';
import { Collapse, CollapseBody, CollapseHeader } from 'accordion-collapse-react-native';
import styles from './styles';

import { round, title, toCurrencyNoSpace } from '../../../utils/StringFormatter';
import Images from '../../../styles/Images';

export default class GlSplit extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      isCollapsed: false,
    };
  }

  render() {
    const { invoice, heading } = this.props;
    const { isCollapsed } = this.state;

    if (invoice) {
      let account_name = '';
      const { account, amount } = invoice;
      let { items } = invoice;
      if (account) account_name = `${account.account_name} (${account.account_number})`;
      if (!items) items = [];
      account_name = title(account_name.trim());

      return (
        <Collapse
          onToggle={(isCollapsed) => this.setState({ isCollapsed })}
          isCollapsed={this.state.isCollapsed}
        >
          <CollapseHeader>
            <View
              style={styles.container}
            >
              <View style={styles.leftView}>
                <Text style={[styles.itemName, account_name ? {} : styles.missingValue]}>{account_name || 'Missing GL Split'}</Text>
              </View>

              <View style={styles.rightView}>
                <Text style={styles.quantity}>
                  {toCurrencyNoSpace(amount)}
                </Text>

                {isCollapsed ? (
                  <Image
                    source={Images.up}
                    style={styles.up_down}
                    resizeMode="contain"
                  />
                ) : (
                  <Image
                    source={Images.down}
                    style={styles.up_down}
                    resizeMode="contain"
                  />
                )}
              </View>
            </View>
          </CollapseHeader>

          <CollapseBody>
            {items && items.length ? (
              <View style={styles.item}>
                <View style={styles.leftItemView}>
                  <Text style={[styles.itemItemName, styles.heading]}>Item Name</Text>
                </View>

                <View style={styles.rightItemView}>
                  <View style={styles.valueView}>
                    <Text style={[styles.itemQuantity, styles.heading]}>Qty</Text>
                  </View>

                  <View style={styles.valueView}>
                    <Text style={[styles.itemQuantity, styles.heading]}>
                      Price
                    </Text>
                  </View>

                  <View style={styles.valueView}>
                    <Text style={[styles.itemQuantity, styles.heading]}>
                      Total
                    </Text>
                  </View>
                </View>
              </View>
            ) : null}

            {items.map((data) => {
              const {
                item, quantity, price, extension
              } = data;
              const display_item_name = item ? title(item.name) : '';

              return (
                <View style={styles.item}>
                  <View style={styles.leftItemView}>
                    <Text style={styles.itemItemName}>{display_item_name}</Text>
                  </View>

                  <View style={styles.rightItemView}>
                    <View style={styles.valueView}>
                      <Text style={styles.itemQuantity}>{round(quantity)}</Text>
                    </View>

                    <View style={styles.valueView}>
                      <Text style={styles.itemQuantity}>
                        {toCurrencyNoSpace(price)}
                      </Text>
                    </View>

                    <View style={styles.valueView}>
                      <Text style={[styles.itemQuantity, styles.bold]}>
                        {toCurrencyNoSpace(extension)}
                      </Text>
                    </View>
                  </View>
                </View>
              );
            })}
          </CollapseBody>

        </Collapse>
      );
    }

    if (heading) {
      return (
        <View style={styles.container}>
          <View style={styles.leftView}>
            <Text style={[styles.left, styles.heading]}>Account Name</Text>
          </View>

          <View style={styles.rightView}>
            <View style={styles.rightView}>
              <Text style={[styles.quantity, styles.heading]}>Amount</Text>
            </View>
          </View>
        </View>
      );
    }

    return null;
  }
}
