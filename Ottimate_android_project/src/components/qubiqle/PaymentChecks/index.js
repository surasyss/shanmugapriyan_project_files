import React from 'react';
import { FlatList } from 'react-native';
import InvoiceEmpty from '../InvoiceEmpty';
import PaymentCheck from '../PaymentCheck';

export default function PaymentChecks(props) {
  let { images } = props;
  const { onPress } = props;
  if (!images) images = [];

  return (
    <FlatList
      data={images}
      renderItem={({ item, index }) => (
        <PaymentCheck
          image={item}
          index={index}
          count={images.length}
          onPress={onPress}
        />
      )}
      ListEmptyComponent={(
        <InvoiceEmpty
          message="There are no payments to display"
        />
            )}
      numColumns={2}
      keyExtractor={(item) => item.toString()}
      listKey={(item, index) => index.toString()}
    />
  );
}
