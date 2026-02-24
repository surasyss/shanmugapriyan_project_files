import React from 'react';
import { FlatList } from 'react-native';
import InvoiceEmpty from '../InvoiceEmpty';
import PaymentInvoice from '../PaymentInvoice';

export default function PaymentInvoiceList(props) {
  let { invoices } = props;
  const { onPress } = props;
  if (!invoices) invoices = [];

  return (
    <FlatList
      data={invoices}
      renderItem={({ item, index }) => (
        <PaymentInvoice
          index={index}
          invoice={item}
          onPress={onPress}
        />
      )}
      ListHeaderComponent={invoices.length ? (
        <PaymentInvoice
          heading
          index={0}
        />
      ) : null}
      ListEmptyComponent={(
        <InvoiceEmpty
          message="There are no Invoices to display"
        />
        )}
      keyExtractor={(item, index) => index.toString()}
      listKey={(item, index) => index.toString()}
    />
  );
}
