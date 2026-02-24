import React from 'react';
import { Text, View } from 'react-native';
import styles from './styles';

import { title, toCurrencyNoSpace } from '../../../utils/StringFormatter';

export default function LineItem(props) {
  const { heading, invoice } = props;

  if (invoice) {
    let item_name = '';
    let account_name = '';
    let
      unit = '';
    const {
      item, account, quantity, price, extension, item_unit
    } = invoice;
    if (item) item_name = item.name;
    if (account) account_name = `${account.account_name} (${account.account_number})`;
    if (item_unit) unit = item_unit.name;
    const display_item_name = title(item_name);
    account_name = title(account_name.trim());

    return (
      <View style={styles.mainView}>
        <View style={styles.container}>
          <View style={styles.leftView}>
            <Text style={styles.itemName}>{display_item_name || 'Item Name'}</Text>
            <Text style={[styles.categoryName, account_name ? {} : styles.missingValue]}>{account_name || 'Missing GL Split'}</Text>
          </View>

          <View style={styles.rightView}>
            <View style={styles.valueView}>
              <Text style={styles.quantity}>{quantity.toFixed(2)}</Text>
            </View>

            <View style={styles.valueView}>
              <Text style={styles.quantity}>
                {toCurrencyNoSpace(price)}
              </Text>
              <Text style={styles.unit}>{unit}</Text>
            </View>

            <View style={styles.valueView}>
              <Text style={styles.quantity}>
                {toCurrencyNoSpace(extension)}
              </Text>
            </View>
          </View>
        </View>
      </View>
    );
  }

  if (heading) {
    return (
      <View style={styles.mainView}>
        <View style={styles.container}>
          <View style={styles.leftView}>
            <Text style={[styles.left, styles.heading]}>Item Name</Text>
          </View>

          <View style={styles.rightView}>
            <View style={styles.valueView}>
              <Text style={[styles.quantity, styles.heading]}>Qty</Text>
            </View>

            <View style={styles.valueView}>
              <Text style={[styles.quantity, styles.heading]}>Price</Text>
            </View>

            <View style={styles.valueView}>
              <Text style={[styles.quantity, styles.heading]}>Total</Text>
            </View>
          </View>
        </View>
      </View>
    );
  }
}
